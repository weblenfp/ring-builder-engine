"""Controller do gerador paramétrico (MVC).

Coordena o aro, a malha web e a compensação térmica. A geometria bruta fica
em ``src/jewelry`` e ``src/core``. Este módulo só instancia, transforma e
delega. Headless: sem ``rhinoscriptsyntax``, ``ActiveDoc`` ou tela.

A raiz do repositório (a pasta que contém ``src/``) precisa estar em
``sys.path`` tanto no GHPython quanto no Rhino.Compute.

.. code-block:: python

    # =====================================================================
    # GHPython — envoltório deste controller
    # =====================================================================
    # O componente Python do Grasshopper não constrói o perfil nem o sweep.
    # Ele lê os painéis, chama ``run_generator`` e publica as três saídas.
    #
    # Inputs do painel (tipo Grasshopper → nome do input):
    #   float   finger_size    Diâmetro interno do dedo, em mm.
    #   float   width          Largura axial do aro, em mm.
    #   float   thickness      Espessura radial do metal, em mm.
    #   str     metal_type     Chave de ``MetalDensity.BY_NAME``
    #                          (``gold_18k`` ou ``platinum``).
    #
    # Outputs do nó (nome do output → variável deste script):
    #   out_web_mesh       Mesh    Malha low-poly do ``base_brep``.
    #                              Escala 1:1, pronta para o .glb / R3F.
    #   out_factory_brep   Brep    NURBS hermético com escala uniforme
    #                              1.025 (+2,5% de shrinkage), pronto
    #                              para o .stl de fábrica.
    #   out_price          float   Massa do metal em gramas, calculada
    #                              no volume 1:1. O banco aplica a tarifa;
    #                              este motor não inventa cotação.
    #
    # Corpo do componente GHPython:
    #
    #   from src.main_generator import run_generator
    #
    #   _result = run_generator(finger_size, width, thickness, metal_type)
    #   out_web_mesh = _result.out_web_mesh
    #   out_factory_brep = _result.out_factory_brep
    #   out_price = _result.out_price
    # =====================================================================
"""

from __future__ import annotations

from typing import NamedTuple

import Rhino.Geometry as rg

from src.core import material_data
from src.core.geometry_utils import convert_brep_to_mesh
from src.jewelry.bands import SolitaireBand

# +2,5%: meio do intervalo de contração térmica previsto no AGENTS.md (2% a 3%).
FACTORY_SCALE: float = 1.025


class GeneratorResult(NamedTuple):
    """Saídas do nó GHPython, na escala de cada canal."""

    out_web_mesh: rg.Mesh
    out_factory_brep: rg.Brep
    out_price: float


def run_generator(
    finger_size: float,
    width: float,
    thickness: float,
    metal_type: str,
) -> GeneratorResult:
    """Gera o par fábrica/web e a massa do aro solitário.

    ``finger_size``, ``width`` e ``thickness`` estão em milímetros.
    ``metal_type`` é a chave de densidade (``gold_18k`` ou ``platinum``).
    A massa usa o sólido 1:1, que é o volume de metal da joia acabada.
    """
    band = SolitaireBand(finger_size, width, thickness)
    base_brep = band.generate_geometry()
    volume_mm3 = band.calculate_volume(base_brep)
    mass_g = material_data.MetalDensity.mass_g(volume_mm3, metal_type)

    factory_brep = _scale_for_factory(base_brep)
    web_mesh = convert_brep_to_mesh(base_brep, is_low_poly=True)

    return GeneratorResult(
        out_web_mesh=web_mesh,
        out_factory_brep=factory_brep,
        out_price=mass_g,
    )


def _scale_for_factory(base_brep: rg.Brep) -> rg.Brep:
    """Copia o sólido 1:1 e aplica a escala uniforme de shrinkage.

    O aro é construído no plano XY com centro na origem, então a âncora
    da escala é a origem: diâmetro e seção crescem juntos 2,5%.
    """
    factory_brep = base_brep.DuplicateBrep()
    if factory_brep is None:
        raise RuntimeError("Não foi possível copiar o Brep para a saída de fábrica.")
    anchor = rg.Point3d.Origin
    factory_brep.Transform(rg.Transform.Scale(anchor, FACTORY_SCALE))
    return factory_brep
