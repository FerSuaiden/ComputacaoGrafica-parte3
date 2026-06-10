# Projeto 3 - Computacao Grafica

**Autores**

- Felipe da Costa Coqueiro - NUSP 11781361
- Fernando Alee Suaiden - NUSP 12680836

Cena 3D em OpenGL para o Projeto 3 da disciplina de Computacao Grafica
(ICMC / USP).

O cenario continua sendo uma balada urbana com ambiente interno e ambiente
externo. A base do Projeto 2 foi mantida, mas o pipeline de renderizacao foi
atualizado para incluir iluminacao ambiente, difusa e especular em shader,
com materiais e texturas definidos no proprio codigo para cada objeto da cena.

Todo o codigo esta em `Projeto_3_Iluminacao_Computacao_Grafica.ipynb`.

## Requisitos Atendidos

- O carro externo continua translacionando por teclado e agora carrega uma
  fonte de luz externa associada a ele.
- Dois objetos internos atuam como luzes coloridas distintas:
  - uma luminaria de teto com luz quente;
  - a bola de discoteca com luz fria.
- A luz externa afeta apenas objetos do ambiente externo.
- As duas luzes internas afetam apenas objetos do ambiente interno.
- A luz ambiente possui interruptor proprio.
- Cada fonte de luz pode ser ligada ou desligada independentemente.
- Existem controles para aumentar e diminuir:
  - a luz ambiente;
  - a reflexao difusa global;
  - a reflexao especular global.
- Cada objeto recebe parametros proprios de material no codigo
  (`ambient_factor`, `diffuse_factor`, `specular_factor`, `shininess`).
- O projeto nao usa arquivos `.mtl`.
- O codigo usa apenas pipeline moderno, sem `glLight`, `glMaterial`,
  `glBegin`, `glEnd`, `glTranslate`, `glRotate`, `glScale` ou matrizes fixas.

## Estrutura

```text
.
├── Projeto_3_Iluminacao_Computacao_Grafica.ipynb
├── README.md
└── assets
    ├── models
    ├── textures
    └── sources/ASSET_SOURCES.txt
```

## Como Executar

Instale as dependencias:

```bash
pip install numpy PyOpenGL glfw PyGLM Pillow notebook ipykernel
```

Abra o notebook:

```bash
jupyter notebook Projeto_3_Iluminacao_Computacao_Grafica.ipynb
```

Execute as celulas em ordem. A ultima celula abre a janela OpenGL.

## Controles

- `W`, `A`, `S`, `D`: mover a camera no plano horizontal.
- `Espaco` / `C`: subir e descer a camera.
- Mouse: olhar ao redor.
- `T` / `G`: transladar o carro externo.
- `0`: ligar ou desligar a luz ambiente.
- `1`: ligar ou desligar a luz externa do carro.
- `2`: ligar ou desligar a luz interna da luminaria.
- `3`: ligar ou desligar a luz interna da bola de discoteca.
- `U` / `J`: aumentar ou diminuir a componente ambiente.
- `I` / `K`: aumentar ou diminuir a reflexao difusa global.
- `O` / `L`: aumentar ou diminuir a reflexao especular global.
- `P`: exibir ou ocultar a malha poligonal.
- `Esc`: fechar a janela.

## Observacoes Tecnicas

- O carregador Wavefront usa apenas os dados geometricos do `.obj`.
- As texturas dos modelos sao associadas manualmente no proprio codigo.
- As normais sao lidas de `vn` quando existem; quando um `.obj` nao traz
  normais, elas sao calculadas por triangulo no carregamento.
- O skybox e desenhado separadamente e nao participa da iluminacao da cena.
- A segmentacao entre ambiente interno e externo e feita com zonas enviadas ao
  shader, o que evita vazamento de luz entre os dois espacos.

## Fontes dos Assets

As origens dos modelos e texturas usados na cena estao documentadas em:

- [assets/sources/ASSET_SOURCES.txt](assets/sources/ASSET_SOURCES.txt)
