"""Aro solitário em meia-cana (perfil D), NURBS fechado, headless.

Usa apenas ``Rhino.Geometry``. Não há ``rhinoscriptsyntax``, ``ActiveDoc``
nem interação com a tela. Unidades: milímetros. Tolerância: 0.001 mm.

GHPython — Inputs do nó
    ring_size_mm (float): diâmetro interno do dedo, em mm.
    width_mm (float): largura axial do aro, em mm.
    thickness_mm (float): espessura radial do metal, em mm.

GHPython — Outputs do nó
    a = band_brep     # rg.Brep sólido hermético, escala 1:1
    b = volume_mm3    # float, volume em mm³
"""

from __future__ import annotations

from typing import Iterable, List

import Rhino.Geometry as rg


class SolitaireBand:
    """Aro de solitário com face interna plana e dorso em meia-elipse.

    A corda do D tem comprimento ``width_mm`` e fica no diâmetro interno.
    A meia-elipse avança ``thickness_mm`` para fora do dedo. Largura e
    espessura são independentes: quando a espessura vale metade da largura,
    o perfil degenera para um semicírculo.
    """

    TOLERANCE: float = 0.001

    def __init__(self, ring_size_mm: float, width_mm: float, thickness_mm: float) -> None:
        self.ring_size_mm = ring_size_mm
        self.width_mm = width_mm
        self.thickness_mm = thickness_mm
        self._validate()

    def generate_geometry(self) -> rg.Brep:
        """Gera o sólido NURBS do aro, fechado e com normal para fora."""
        inner_radius = self.ring_size_mm / 2.0
        rail = self._finger_rail(inner_radius)
        profile = self._d_profile()
        profile.Transform(self._section_transform(rail))

        swept = rg.Brep.CreateFromSweep(rail, profile, True, self.TOLERANCE)
        if not swept:
            raise RuntimeError("CreateFromSweep não gerou o aro.")
        return self._as_outward_solid(swept)

    def calculate_volume(self, brep: rg.Brep) -> float:
        """Volume matemático do sólido, em mm³.

        Lê ``VolumeMassProperties`` sem alterar o Brep recebido.
        """
        if brep is None or not brep.IsValid or not brep.IsSolid:
            raise ValueError("O volume exige um Brep sólido e válido.")
        props = rg.VolumeMassProperties.Compute(brep)
        if props is None:
            raise RuntimeError("Não foi possível calcular o volume do aro.")
        return abs(float(props.Volume))

    def _validate(self) -> None:
        if self.ring_size_mm <= 0.0:
            raise ValueError("ring_size_mm deve ser o diâmetro interno positivo, em mm.")
        if self.width_mm <= 0.0:
            raise ValueError("width_mm deve ser a largura axial positiva, em mm.")
        if self.thickness_mm <= 0.0:
            raise ValueError("thickness_mm deve ser a espessura radial positiva, em mm.")
        if self.thickness_mm >= self.ring_size_mm / 2.0:
            raise ValueError("thickness_mm precisa ser menor que o raio interno do dedo.")

    def _finger_rail(self, inner_radius: float) -> rg.Curve:
        """Círculo do dedo no plano XY. O eixo do aro é Z.

        A seção usa X radial e Y = +Z. O produto ``radial × Z`` aponta no
        sentido horário, então o círculo é invertido para a tangente
        coincidir com a normal do plano do perfil.
        """
        circle = rg.Circle(rg.Plane.WorldXY, inner_radius)
        rail = circle.ToNurbsCurve()
        if rail is None:
            raise RuntimeError("Falha ao converter o círculo do dedo em NURBS.")
        rail.Reverse()
        return rail

    def _d_profile(self) -> rg.Curve:
        """Perfil D no plano XY: corda no eixo Y, bojo no eixo X positivo.

        X local será mapeado para fora do dedo. Y local será mapeado para +Z.
        """
        half_width = self.width_mm / 2.0
        ellipse = rg.Ellipse(rg.Plane.WorldXY, self.thickness_mm, half_width)
        outline = ellipse.ToNurbsCurve()
        if outline is None:
            raise RuntimeError("Falha ao criar a elipse da meia-cana.")

        top = rg.Point3d(0.0, half_width, 0.0)
        bottom = rg.Point3d(0.0, -half_width, 0.0)
        outer_half = self._half_through_point(
            outline,
            top,
            bottom,
            rg.Point3d(self.thickness_mm, 0.0, 0.0),
        )
        flat = rg.LineCurve(outer_half.PointAtEnd, outer_half.PointAtStart)
        return self._join_closed([outer_half, flat])

    def _half_through_point(
        self,
        curve: rg.Curve,
        first: rg.Point3d,
        second: rg.Point3d,
        interior: rg.Point3d,
    ) -> rg.Curve:
        """Metade da curva fechada que passa por ``interior``."""
        found_first, t_first = curve.ClosestPoint(first)
        found_second, t_second = curve.ClosestPoint(second)
        if not found_first or not found_second:
            raise RuntimeError("Não foi possível partir o perfil D.")

        pieces = curve.Split([t_first, t_second])
        if not pieces:
            raise RuntimeError("A elipse da meia-cana não pôde ser dividida.")

        for piece in pieces:
            midpoint = piece.PointAt(piece.Domain.Mid)
            if midpoint.DistanceTo(interior) < self.TOLERANCE or midpoint.X > 0.0:
                return piece
        raise RuntimeError("A metade externa do perfil D não foi encontrada.")

    def _join_closed(self, curves: Iterable[rg.Curve]) -> rg.Curve:
        joined = rg.Curve.JoinCurves(list(curves), self.TOLERANCE)
        if not joined or len(joined) != 1:
            raise RuntimeError("Não foi possível fechar o perfil D.")
        profile = joined[0]
        if not profile.IsClosed:
            profile.MakeClosed(self.TOLERANCE)
        if not profile.IsClosed or not profile.IsPlanar(self.TOLERANCE):
            raise RuntimeError("O perfil D precisa ser uma curva plana fechada.")
        return profile

    def _section_transform(self, rail: rg.Curve) -> rg.Transform:
        """Posiciona o perfil no início do círculo, perpendicular à tangente.

        ``radial`` sai do centro do dedo. ``up`` é o eixo do aro. A normal
        do plano resultante é ``radial × up`` e acompanha o trilho invertido.
        """
        seam = rail.PointAtStart
        tangent = rail.TangentAtStart
        radial = rg.Vector3d(seam)
        up = rg.Vector3d.ZAxis
        if not radial.Unitize() or not tangent.Unitize() or not up.Unitize():
            raise RuntimeError("Não foi possível orientar a seção no círculo.")

        section_plane = rg.Plane(seam, radial, up)
        return rg.Transform.PlaneToPlane(rg.Plane.WorldXY, section_plane)

    def _as_outward_solid(self, breps: Iterable[rg.Brep]) -> rg.Brep:
        pieces: List[rg.Brep] = list(breps)
        if len(pieces) == 1:
            brep = pieces[0]
        else:
            joined = rg.Brep.JoinBreps(pieces, self.TOLERANCE)
            if not joined:
                raise RuntimeError("Não foi possível unir as faces do sweep.")
            brep = joined[0]

        if not brep.IsSolid:
            capped = brep.CapPlanarHoles(self.TOLERANCE)
            if capped is not None:
                brep = capped
        if not brep.IsSolid:
            raise RuntimeError("O sweep da meia-cana não fechou um sólido hermético.")
        if brep.SolidOrientation == rg.BrepSolidOrientation.Inward:
            brep.Flip()
        return brep
