"""Densidades de metais para converter volume (mm³) em massa (g).

O volume vem de ``VolumeMassProperties`` do Brep, em mm³. As densidades
abaixo já estão em g/mm³ (equivalente a g/cm³ dividido por 1000).

GHPython — Inputs do nó
    metal_key (str): chave em ``MetalDensity.BY_NAME``, por exemplo ``gold_18k``.
    volume_mm3 (float): volume do sólido, em mm³.

GHPython — Outputs do nó
    a = density_g_per_mm3
    b = mass_g
"""

from typing import Dict, Final


class MetalDensity:
    """Densidades estáticas dos metais usados na precificação."""

    GOLD_18K_G_PER_MM3: Final[float] = 0.0155
    """Ouro 18k. 15.5 g/cm³."""

    PLATINUM_G_PER_MM3: Final[float] = 0.0214
    """Platina. 21.4 g/cm³."""

    BY_NAME: Dict[str, float] = {
        "gold_18k": GOLD_18K_G_PER_MM3,
        "platinum": PLATINUM_G_PER_MM3,
    }

    @staticmethod
    def density_g_per_mm3(metal_key: str) -> float:
        """Devolve a densidade em g/mm³ para a chave informada."""
        try:
            return MetalDensity.BY_NAME[metal_key]
        except KeyError as exc:
            known = ", ".join(sorted(MetalDensity.BY_NAME))
            raise KeyError(f"Metal desconhecido: {metal_key}. Use: {known}.") from exc

    @staticmethod
    def mass_g(volume_mm3: float, metal_key: str) -> float:
        """Massa em gramas a partir do volume do sólido e do metal."""
        if volume_mm3 < 0.0:
            raise ValueError("volume_mm3 não pode ser negativo.")
        return volume_mm3 * MetalDensity.density_g_per_mm3(metal_key)
