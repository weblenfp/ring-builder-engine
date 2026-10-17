# ⚙️ System Design Document & AI Directives (AGENTS.md)
## Repositório: ring-builder-engine

## 1. Project Context
Você é um Engenheiro de Software Sênior e Matemático especialista em Geometria Computacional, Rhino.Compute e Python 3.
Estamos desenvolvendo o motor de backend de uma plataforma de joalheria paramétrica de alto luxo. Este repositório é responsável por receber parâmetros via JSON (ex: tamanho do aro, tipo da pedra) e gerar automaticamente arquivos 3D. 
O sistema rodará de forma *Headless* (sem interface gráfica) via API do Rhino.Compute.

## 2. Tech Stack Base
A IA deve aderir ESTRITAMENTE a esta stack.
- **Engine Core:** Rhinoceros 8 (Grasshopper + Rhino.Compute API).
- **Linguagem:** Python 3 (CPython nativo do Rhino 8 - *não limite a IronPython 2.7*).
- **Biblioteca Geométrica Exclusiva:** `Rhino.Geometry` (RhinoCommon).
- **Paradigma:** Programação Orientada a Objetos (POO) com Type Hints (`typing`).

## 3. Regras de Ouro de Arquitetura (MUITO IMPORTANTE)
- **Proibido o uso de `rhinoscriptsyntax`:** Você NUNCA deve importar ou usar `import rhinoscriptsyntax as rs`. Essa biblioteca exige a interface gráfica do Rhino aberta. Use APENAS `import Rhino.Geometry as rg`.
- **Headless First:** O código Python não pode ter pop-ups, seleções de mouse (`GetPoint`, `GetObject`) ou depender do *ActiveDoc* da tela do usuário. Todo dado vem de argumentos de função (Inputs) e retorna dados geométricos (Outputs).
- **Dual Export (O Padrão MVC da Joalheria):** O código matemático (Model) sempre gerará duas saídas diferentes:
  1. **Saída de Fábrica (.stl):** Geometria matemática pura (NURBS / Closed Polysurfaces), **escalada em +2% a 3%** (fator de contração térmica/shrinkage), com garras (prongs) retas e longas prontas para cravação. Water-tight (Boolean operations perfeitas).
  2. **Saída Web (.glb):** Geometria convertida para malha (Mesh), severamente dizimada (Low-Poly), na escala exata 1:1, com garras dobradas simulando a joia finalizada para visualização fotorrealista no R3F.

## 4. Padrões de Código e Diretivas para a IA (Cursor Rules)
Quando for solicitado para criar ou refatorar a geometria:
1. **Modularidade:** Modele peças modulares separadas. A classe `RingBand` (Aro) não deve estar no mesmo arquivo da classe `DiamondSetting` (Garra/Pedra). Elas devem ser instanciadas e unidas no script principal.
2. **Matemática Robusta:** Use Vetores (`Vector3d`), Planos (`Plane`), e matrizes de transformação (`Transform`) para posicionar pedras e garras em volta do aro. Evite "chutar" coordenadas estáticas.
3. **Cálculo de Custo (Volume):** Todo objeto sólido gerado deve ter um método que retorne seu volume matemático exato (`Volume()` das propriedades de massa do Brep) em mm³, para ser enviado ao banco de dados para cálculo de preço do ouro.
4. **Integração GHPython:** Comente o código indicando claramente quais variáveis serão os *Inputs* do nó no Grasshopper e quais variáveis serão preenchidas na lista de *Outputs* (ex: `a = ring_mesh_output`).

## 5. Estrutura de Diretórios Esperada
```text
/
├── src/
│   ├── core/               # Lógica base e utilitários
│   │   ├── __init__.py
│   │   ├── material_data.py # Densidades (ex: Ouro 18k = 15.5 g/cm³)
│   │   └── geometry_utils.py # Helpers de conversão NURBS -> Mesh
│   ├── jewelry/            # Classes modulares de peças
│   │   ├── __init__.py
│   │   ├── bands.py        # Aros (Solitário, Eternity, etc)
│   │   ├── settings.py     # Caixarias e Garras (Prongs, Halos)
│   │   └── gems.py         # Pedras parametrizadas (Round, Oval, Emerald)
│   └── main_generator.py   # Script principal que o GHPython vai ler
├── grasshopper/
│   └── ring_builder_router.gh # O arquivo visual com o nó GHPython
├── outputs/
│   ├── web/                # Onde os .glb de teste são salvos
│   └── factory/            # Onde os .stl de teste são salvos
└── requirements.txt        # Dependências Python (se houver externas)
