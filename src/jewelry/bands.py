"""Aro solitário em meia-cana (perfil D), NURBS fechado, headless.

Este módulo usa apenas ``Rhino.Geometry`` (RhinoCommon). Ele não abre o
Rhino, não lê ``ActiveDoc`` e não importa ``rhinoscriptsyntax``.

Execução esperada: CPython 3 do Rhino 8, Grasshopper (GHPython) ou
Rhino.Compute. Unidades do modelo: milímetros.

GHPython — Inputs do nó
    size_mm (float): diâmetro interno do dedo, em mm.
    thickness_mm (float): raio da meia-cana (espessura radial), em mm.
        A altura axial do perfil D é ``2 * thickness_mm``.

GHPython — Outputs do nó
    a = band_brep    # rg.Brep sólido (NURBS fechado), escala 1:1
    b = volume_mm3   # float, volume em mm³ (VolumeMassProperties)
"""

from __future__ import annotations

import math
from typing import Optional, Tuple

import Rhino.Geometry as rg


class SolitaireBand:
    """Gera o aro de um solitário com seção meia-cana (D-shape).

    A face plana da letra D fica no diâmetro interno (contato com o dedo).
    O arco semicircular fecha a seção para fora. O sólido é o sweep fechado
    desse perfil sobre o círculo do dedo.
    """

    def __init__(self, tolerance: float = 0.001) -> None:
        if tolerance <= 0.0:
            raise ValueError("tolerance deve ser positiva.")
        self.tolerance: float = tolerance
        self._brep: Optional[rg.Brep] = None

    def generate_band(self, size_mm: float, thickness_mm: float) -> Tuple[rg.Brep, float]:
        """Constrói o sólido e devolve o Brep junto com o volume em mm³.

        Parameters
        ----------
        size_mm:
            Diâmetro interno do dedo, em milímetros.
        thickness_mm:
            Espessura radial da meia-cana, em milímetros. A altura do perfil
            (corda da letra D) é o dobro desse valor.
        """
        inner_radius = self._validate(size_mm, thickness_mm)
        rail = self._finger_circle(inner_radius)
        profile = self._d_profile(thickness_mm)
        profile.Transform(self._profile_transform(rail))

        brep = self._sweep_closed(rail, profile)
        brep = self._as_outward_solid(brep)
        self._brep = brep
        return brep, self.volume_mm3()

    def volume_mm3(self) -> float:
        """Volume matemático do último sólido gerado, em mm³.

        Usa ``VolumeMassProperties.Compute`` sobre o Brep fechado. O valor
        alimenta o cálculo de massa do ouro no banco.
        """
        if self._brep is None:
            raise RuntimeError("Nenhum sólido gerado. Chame generate_band antes.")
        props = rg.VolumeMassProperties.Compute(self._brep)
        if props is None:
            raise RuntimeError("O Brep não possui volume calculável.")
        return float(props.Volume)

    def _validate(self, size_mm: float, thickness_mm: float) -> float:
        if size_mm <= 0.0:
            raise ValueError("size_mm deve ser o diâmetro interno positivo, em mm.")
        if thickness_mm <= 0.0:
            raise ValueError("thickness_mm deve ser a espessura radial positiva, em mm.")
        inner_radius = size_mm / 2.0
        if thickness_mm >= inner_radius:
            raise ValueError(
                "thickness_mm precisa ser menor que o raio interno do dedo."
            )
        return inner_radius

    def _finger_circle(self, inner_radius: float) -> rg.NurbsCurve:
        """Círculo do dedo no plano XY, eixo do aro em Z."""
        circle = rg.Circle(rg.Plane.WorldXY, inner_radius)
        rail = circle.ToNurbsCurve()
        if rail is None:
            raise RuntimeError("Falha ao converter o círculo do dedo em NURBS.")
        # O plano do perfil usa X radial e Y = +Z. O produto vetorial aponta
        # para o sentido oposto ao tangente CCW, então o trilho é invertido
        # para a normal do perfil coincidir com a direção do sweep.
        rail.Reverse()
        return rail

    def _d_profile(self, thickness_mm: float) -> rg.Curve:
        """Perfil D canônico no plano XY, corda sobre o eixo Y.

        A corda (x = 0) é a face interna. O arco passa por (thickness, 0),
        que o ``PlaneToPlane`` leva para fora do dedo.
        """
        top = rg.Point3d(0.0, thickness_mm, 0.0)
        outer = rg.Point3d(thickness_mm, 0.0, 0.0)
        bottom = rg.Point3d(0.0, -thickness_mm, 0.0)

        flat = rg.LineCurve(bottom, top)
        arc = rg.Arc(top, outer, bottom)
        if not arc.IsValid:
            raise RuntimeError("O arco da meia-cana é inválido.")

        joined = rg.Curve.JoinCurves([flat, arc.ToNurbsCurve()], self.tolerance)
        if not joined or len(joined) != 1:
            raise RuntimeError("Não foi possível fechar o perfil D.")

        profile = joined[0]
        if not profile.IsClosed:
            profile.MakeClosed(self.tolerance)
        if not profile.IsClosed or not profile.IsPlanar(self.tolerance):
            raise RuntimeError("O perfil D precisa ser uma curva plana fechada.")
        return profile

    def _profile_transform(self, rail: rg.Curve) -> rg.Transform:
        """Leva o perfil do plano XY para a seção no início do círculo.

        X local → radial para fora, Y local → +Z (altura do aro).
        """
        start = rail.PointAtStart
        tangent = rail.TangentAtStart
        radial = rg.Vector3d(start)
        if not radial.Unitize() or not tangent.Unitize():
            raise RuntimeError("Não foi possível orientar a seção no círculo.")

        frame = rg.Plane(start, radial, rg.Vector3d.ZAxis)
        return rg.Transform.PlaneToPlane(rg.Plane.WorldXY, frame)

    def _sweep_closed(self, rail: rg.Curve, profile: rg.Curve) -> rg.Brep:
        sweep = rg.SweepOneRail()
        sweep.ClosedSweep = True
        sweep.SweepTolerance = self.tolerance
        sweep.AngleToleranceRadians = math.radians(1.0)
        sweep.SetToRoadlikeTop()

        breps = sweep.PerformSweep(rail, profile)
        if not breps:
            raise RuntimeError("Sweep1 não gerou o sólido do aro.")
        return breps[0]

    def _as_outward_solid(self, brep: rg.Brep) -> rg.Brep:
        if not brep.IsSolid:
            capped = brep.CapPlanarHoles(self.tolerance)
            if capped is not None:
                brep = capped
        if not brep.IsSolid:
            raise RuntimeError("O sweep da meia-cana não fechou um sólido.")
        if brep.SolidOrientation == rg.BrepSolidOrientation.Inward:
            brep.Flip()
        return brep


if __name__ == "__main__":
    # GHPython: estes literais seriam os Inputs do componente.
    # Outputs: a = band_brep, b = volume_mm3.
    size_mm = 17.0
    thickness_mm = 2.0

    band = SolitaireBand()
    band_brep, volume_mm3 = band.generate_band(size_mm, thickness_mm)
    print(f"SolitaireBand diâmetro={size_mm} mm, espessura={thickness_mm} mm")
    print(f"Sólido fechado: {band_brep.IsSolid}")
    print(f"Volume: {volume_mm3} mm³")
