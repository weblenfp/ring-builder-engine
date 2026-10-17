"""Conversão headless de NURBS (Brep) para malha.

Usa apenas ``Rhino.Geometry``. Não há ``rhinoscriptsyntax``, ``ActiveDoc``
nem interação com a tela. A malha leve alimenta o GLB web em escala 1:1.
A malha detalhada serve para inspeção; o STL de fábrica continua NURBS.

GHPython — Inputs do nó
    brep (rg.Brep): sólido ou polissuperfície fechada.
    is_low_poly (bool): True para malha web leve; False para malha densa.

GHPython — Outputs do nó
    a = mesh
"""

from __future__ import annotations

import Rhino.Geometry as rg


def convert_brep_to_mesh(brep: rg.Brep, is_low_poly: bool = True) -> rg.Mesh:
    """Extrai uma malha do Brep com parâmetros leves ou detalhados.

    ``is_low_poly=True`` limita o comprimento de aresta e desliga o refino,
    para uma malha pequena o bastante para o visualizador web. ``False``
    usa tolerância mais justa e refino de grade.
    """
    if brep is None or not brep.IsValid:
        raise ValueError("brep precisa ser um Brep válido.")

    parameters = _low_poly_parameters() if is_low_poly else _detailed_parameters()
    pieces = rg.Mesh.CreateFromBrep(brep, parameters)
    if not pieces:
        raise RuntimeError("A extração de malha não produziu faces.")

    mesh = rg.Mesh()
    for piece in pieces:
        mesh.Append(piece)
    mesh.Compact()
    return mesh


def _low_poly_parameters() -> rg.MeshingParameters:
    """Parâmetros de extração muito leves, em milímetros."""
    parameters = rg.MeshingParameters(rg.MeshingParameters.Coarse)
    parameters.SimplePlanes = True
    parameters.RefineGrid = False
    parameters.JaggedSeams = True
    parameters.GridAmplification = 1.0
    parameters.GridMinCount = 0
    parameters.RelativeTolerance = 0.2
    parameters.MinimumEdgeLength = 0.4
    parameters.MaximumEdgeLength = 1.5
    return parameters


def _detailed_parameters() -> rg.MeshingParameters:
    """Parâmetros de extração mais justos, em milímetros."""
    parameters = rg.MeshingParameters(rg.MeshingParameters.Smooth)
    parameters.SimplePlanes = False
    parameters.RefineGrid = True
    parameters.JaggedSeams = False
    parameters.GridAmplification = 1.5
    parameters.RelativeTolerance = 0.01
    parameters.MinimumEdgeLength = 0.02
    parameters.MaximumEdgeLength = 0.2
    return parameters
