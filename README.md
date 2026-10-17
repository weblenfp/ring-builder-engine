# ring-builder-engine

Motor headless de joalheria paramétrica. Ele recebe o tamanho do dedo, a seção do aro e o metal, e devolve duas geometrias: uma malha leve em escala real para a web e um sólido NURBS ampliado para a fábrica, além da massa do metal em gramas.

A geometria roda no CPython 3 do Rhinoceros 8, via Grasshopper ou Rhino.Compute. Não há janela, seleção de mouse nem dependência do documento ativo.

## Arquitetura

O fluxo segue um MVC enxuto. O model constrói o sólido. O controller só delega e aplica a escala de cada canal.

```text
painéis GHPython / Rhino.Compute
        │
        ▼
src/main_generator.py          controller
        │
        ├── src/jewelry/bands.py        model: aro solitário em meia-cana
        ├── src/core/material_data.py   densidade → massa em gramas
        └── src/core/geometry_utils.py  Brep NURBS → malha
```

| Módulo | Papel |
| --- | --- |
| `src/jewelry/bands.py` | `SolitaireBand` cria o círculo do dedo, o perfil D e o sweep fechado. |
| `src/core/material_data.py` | Densidades em g/mm³. Ouro 18k = 0,0155. Platina = 0,0214. |
| `src/core/geometry_utils.py` | `convert_brep_to_mesh` extrai malha leve ou densa. |
| `src/main_generator.py` | `run_generator` monta o par fábrica/web e a massa. |

`SolitaireBand` usa somente `Rhino.Geometry`. `rhinoscriptsyntax` fica de fora: essa biblioteca exige a interface gráfica do Rhino.

## Saídas geradas

`run_generator(finger_size, width, thickness, metal_type)` devolve um `GeneratorResult`:

| Campo | O que é | Escala |
| --- | --- | --- |
| `out_web_mesh` | Malha low-poly do aro, pronta para exportar `.glb` e visualizar no R3F. | 1:1 |
| `out_factory_brep` | Brep NURBS hermético, pronto para exportar `.stl`. | 1,025 (+2,5% de contração térmica) |
| `out_price` | Massa do metal em gramas, calculada no volume 1:1. | — |

A massa usa o sólido em escala real, que é o volume de metal da joia acabada. A ampliação de 2,5% existe só no modelo de fundição. O motor não aplica cotação: o banco converte a massa em preço.

As pastas abaixo estão reservadas para os arquivos de teste. O controller ainda não grava disco; quem exporta é o Grasshopper ou o Rhino.Compute. O `.gitignore` ignora esses binários e preserva as pastas.

```text
outputs/web/       .glb de visualização
outputs/factory/   .stl de fabricação
```

## Requisitos

- Rhinoceros 8, com Grasshopper.
- CPython 3 distribuído com o Rhino 8. Não use o IronPython 2.7.
- Nenhuma dependência pip. `Rhino.Geometry` já vem com o Rhino.

Não há `requirements.txt` nesta etapa.

## Setup

1. Clone o repositório.
2. Instale o Rhinoceros 8.
3. No componente Python 3 do Grasshopper, ou no ScriptEditor do Rhino 8, coloque a raiz do repositório em `sys.path`. A raiz é a pasta que contém `src/`.

```python
import sys
sys.path.insert(0, "/caminho/para/ring-builder-engine")
```

## Como executar

No componente GHPython, os inputs do painel são `finger_size`, `width`, `thickness` e `metal_type`. Os outputs do nó são `out_web_mesh`, `out_factory_brep` e `out_price`.

```python
from src.main_generator import run_generator

_result = run_generator(finger_size, width, thickness, metal_type)
out_web_mesh = _result.out_web_mesh
out_factory_brep = _result.out_factory_brep
out_price = _result.out_price
```

Unidades em milímetros. `metal_type` aceita `gold_18k` ou `platinum`.

Exemplo de aro tamanho 17, largura 3 mm e espessura radial 1,8 mm:

```python
from src.main_generator import run_generator

result = run_generator(17.0, 3.0, 1.8, "gold_18k")
print(result.out_price)  # massa em gramas
```

Esse script só importa `Rhino.Geometry` dentro do processo do Rhino 8. Um Python do sistema não resolve esse módulo.

Para gravar os testes, exporte `out_factory_brep` como `.stl` em `outputs/factory/` e `out_web_mesh` como `.glb` em `outputs/web/`.
