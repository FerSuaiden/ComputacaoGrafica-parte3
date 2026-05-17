from __future__ import annotations

import json
from pathlib import Path


def lines(text: str) -> list[str]:
    text = text.strip("\n")
    return [line + "\n" for line in text.splitlines()]


NOTEBOOK_PATH = Path(__file__).with_name("Projeto_2_Computacao_Grafica.ipynb")


markdown_intro = """
# Projeto 3 - Computacao Grafica

## Felipe da Costa Coqueiro, NUSP: 11781361
## Fernando Alee Suaiden, NUSP: 12680836

Cena 3D: **balada urbana com iluminacao segmentada entre ambiente interno e ambiente externo**.

Esta versao transforma o Projeto 2 em uma entrega do **Projeto 3**. A cena base foi mantida: clube fechado com pista, pessoas, palco, sofas, cadeiras, luminarias, bola de discoteca e area externa com estacionamento, entrada metalica, carro, postes e lixeira. A principal mudanca esta no pipeline de renderizacao: agora o notebook usa **iluminacao ambiente, difusa e especular calculada em shader**, com **materiais e texturas definidos no proprio codigo** para cada objeto da cena, sem usar arquivos `.mtl`.

Os requisitos foram atendidos da seguinte forma:

- o **carro externo** continua translacionando e agora carrega uma **fonte de luz externa** associada a ele;
- dois objetos internos atuam como luzes com cores diferentes: uma **luminaria de teto** e a **bola de discoteca**;
- cada luz pode ser ligada ou desligada de forma independente, e a luz ambiente tambem possui interruptor proprio;
- ha teclas para aumentar e diminuir ambiente, reflexao difusa e reflexao especular;
- objetos internos recebem apenas luzes internas, e objetos externos recebem apenas a luz externa;
- toda a iluminacao e implementada em **pipeline moderno**, sem `glLight`, `glMaterial`, `glBegin`, `glEnd` ou matrizes fixas do OpenGL.
"""


markdown_paths = """
## 1. Dependencias e estrutura da cena

Usamos apenas `PyOpenGL`, `glfw`, `numpy`, `PyGLM` e `Pillow`. O notebook localiza a pasta `assets` automaticamente, carrega modelos Wavefront `.obj` e define, no proprio Python, tanto as **texturas** quanto os **parametros de iluminacao** de cada objeto.

Cada instancia da cena recebe seus proprios parametros:

- `ambient_factor`: peso do termo ambiente no objeto;
- `diffuse_factor`: quanto ele reage a luz difusa;
- `specular_factor`: quanto ele reage ao brilho especular;
- `shininess`: expoente especular;
- `emissive_color` e `emissive_strength`: brilho proprio de objetos-fonte.

Tambem classificamos cada objeto como pertencente ao `INTERIOR`, `EXTERIOR` ou `SHARED`, o que permite mascarar quais luzes realmente o afetam sem deixar objetos de transicao completamente apagados.
"""


code_main = r'''
from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
import ctypes
import math

import glfw
from OpenGL.GL import *
import glm
import numpy as np
from PIL import Image


def find_project_root():
    """Localiza a pasta que contem assets/models mesmo se o notebook for aberto pela raiz do workspace."""
    search_roots = [Path.cwd(), *Path.cwd().parents]
    candidates = []
    for root in search_roots:
        candidates.append(root)
        candidates.append(root / "ComputacaoGrafica")

    for candidate in candidates:
        if (candidate / "assets" / "models").is_dir() and (candidate / "assets" / "textures").is_dir():
            return candidate.resolve()

    raise FileNotFoundError(
        "Nao encontrei a pasta assets/models do projeto. Abra o notebook dentro da pasta ComputacaoGrafica ou do workspace clonado."
    )


BASE_DIR = find_project_root()
ASSETS_DIR = BASE_DIR / "assets"
MODELS_DIR = ASSETS_DIR / "models"
TEXTURES_DIR = ASSETS_DIR / "textures"


MODEL_TEXTURES = {
    "bar_chair_round_01": TEXTURES_DIR / "bar_chair_round_01_bar_chair_round_01_diff_1k.jpg",
    "boombox": TEXTURES_DIR / "boombox_boombox_diff_1k.jpg",
    "corrado_car_01": TEXTURES_DIR / "corrado_car_01_diffuse.png",
    "dance_floor": TEXTURES_DIR / "dance_floor_checkered_pavement_tiles_diff_1k.jpg",
    "disco_ball": TEXTURES_DIR / "disco_ball_basecolor.jpg",
    "disco_support": TEXTURES_DIR / "disco_metal_plate_diff_1k.jpg",
    "lounge_floor": TEXTURES_DIR / "club_accent_painted_concrete_diff_1k.jpg",
    "modern_ceiling_lamp_01": TEXTURES_DIR / "modern_ceiling_lamp_01_modern_ceiling_lamp_01_diff_1k.jpg",
    "night_skybox": TEXTURES_DIR / "night_sky_clean.png",
    "oga_trash_can_01": TEXTURES_DIR / "oga_trash_can_01_diffuse.png",
    "parking_lot": TEXTURES_DIR / "parking_asphalt_07_diff_1k.jpg",
    "party_person_male_01": MODELS_DIR / "CMan0010.tif",
    "rollershutter_door": TEXTURES_DIR / "rollershutter_door_rollershutter_door_diff_1k.jpg",
    "sofa_01": TEXTURES_DIR / "sofa_01_Sofa_01_diff_1k.jpg",
    "street_lamp_01": TEXTURES_DIR / "street_lamp_01_street_lamp_01_diff_1k.jpg",
}

MODEL_SUBMESH_TEXTURES = {
    "boombox": {
        "boombox": TEXTURES_DIR / "boombox_boombox_diff_1k.jpg",
        "boombox_speakers": TEXTURES_DIR / "boombox_boombox_speakers_diff_1k.jpg",
    },
    "club_room": {
        "club_wall": TEXTURES_DIR / "club_wall_black_painted_planks_diff_1k.jpg",
        "club_ceiling": TEXTURES_DIR / "club_ceiling_square_tiles_03_diff_1k.jpg",
    },
    "modern_ceiling_lamp_01": {
        "modern_ceiling_lamp_01_glass": TEXTURES_DIR / "modern_ceiling_lamp_01_modern_ceiling_lamp_01_diff_1k.jpg",
        "modern_ceiling_lamp_01": TEXTURES_DIR / "modern_ceiling_lamp_01_modern_ceiling_lamp_01_diff_1k.jpg",
        "modern_ceiling_globe": TEXTURES_DIR / "modern_ceiling_lamp_01_modern_ceiling_lamp_01_diff_1k.jpg",
    },
    "party_person_01": {
        "Material__61": MODELS_DIR / "12b3dc50.dds",
        "Material__62": MODELS_DIR / "1711d670.dds",
        "Material__63": MODELS_DIR / "12b3dd50.dds",
        "Material__60": MODELS_DIR / "12d945f0.dds",
        "Material__64": MODELS_DIR / "12c2a390.dds",
        "Material__65": MODELS_DIR / "12c56a50.dds",
    },
}

ZONE_SHARED = 0
ZONE_INTERIOR = 1
ZONE_EXTERIOR = 2
MAX_LIGHTS = 4

print("Pasta base:", BASE_DIR)
print("Pasta de modelos:", MODELS_DIR)
print("Pasta de texturas:", TEXTURES_DIR)
'''


markdown_shader = """
## 2. Shader com Phong e mascaramento por ambiente

O vertex shader agora envia para o fragment shader:

- a coordenada de textura;
- a posicao do fragmento no espaco do mundo;
- a normal transformada pela `normalMatrix`.

No fragment shader usamos um modelo de Phong com:

- termo ambiente global com interruptor e intensidade ajustavel;
- ate quatro luzes, incluindo dois farois externos vinculados ao mesmo carro;
- mascaramento por zona (`INTERIOR`, `EXTERIOR` ou `SHARED`), de modo que a luz externa nao ilumine o clube e as luzes internas nao vazem para fora;
- material do objeto enviado via `uniform`, sem usar `.mtl`.
"""


code_shader = r'''
VERTEX_SHADER_SOURCE = """
#version 330 core
layout (location = 0) in vec3 position;
layout (location = 1) in vec2 texcoord;
layout (location = 2) in vec3 normal;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;
uniform mat3 normalMatrix;

out vec2 uv;
out vec3 fragPos;
out vec3 fragNormal;

void main() {
    vec4 worldPosition = model * vec4(position, 1.0);
    gl_Position = projection * view * worldPosition;
    uv = texcoord;
    fragPos = worldPosition.xyz;
    fragNormal = normalize(normalMatrix * normal);
}
"""

FRAGMENT_SHADER_SOURCE = """
#version 330 core
in vec2 uv;
in vec3 fragPos;
in vec3 fragNormal;

out vec4 FragColor;

uniform sampler2D imageTexture;
uniform vec3 baseColor;
uniform vec3 viewPos;
uniform bool unlit;
uniform vec3 emissiveColor;
uniform float emissiveStrength;

uniform bool ambientEnabled;
uniform float ambientLevel;
uniform int objectZone;
uniform float globalDiffuseLevel;
uniform float globalSpecularLevel;

uniform float materialAmbient;
uniform float materialDiffuse;
uniform float materialSpecular;
uniform float materialShininess;

uniform vec3 lightPos[4];
uniform vec3 lightColor[4];
uniform float lightIntensity[4];
uniform bool lightEnabled[4];
uniform int lightZone[4];
uniform bool lightIsSpot[4];
uniform vec3 lightDirection[4];
uniform float lightCutoffCos[4];

void main() {
    vec3 albedo = texture(imageTexture, uv).rgb * baseColor;
    if (unlit) {
        FragColor = vec4(albedo, 1.0);
        return;
    }
    vec3 normal = normalize(gl_FrontFacing ? fragNormal : -fragNormal);
    vec3 viewDir = normalize(viewPos - fragPos);

    vec3 color = emissiveColor * emissiveStrength;

    if (ambientEnabled) {
        color += albedo * materialAmbient * ambientLevel;
    }

    for (int i = 0; i < 4; ++i) {
        if (!lightEnabled[i]) {
            continue;
        }
        if (objectZone != 0 && lightZone[i] != objectZone) {
            continue;
        }

        vec3 lightDir = normalize(lightPos[i] - fragPos);
        float distanceToLight = length(lightPos[i] - fragPos);
        float attenuation = 1.0 / (1.0 + 0.035 * distanceToLight + 0.004 * distanceToLight * distanceToLight);
        float spotFactor = 1.0;

        if (lightIsSpot[i]) {
            float spotCos = dot(normalize(lightDirection[i]), normalize(fragPos - lightPos[i]));
            if (spotCos < lightCutoffCos[i]) {
                continue;
            }
            spotFactor = smoothstep(lightCutoffCos[i], min(1.0, lightCutoffCos[i] + 0.05), spotCos);
        }

        float diff = max(dot(normal, lightDir), 0.0);
        vec3 diffuse = albedo * materialDiffuse * globalDiffuseLevel * diff * lightColor[i];

        vec3 reflectDir = reflect(-lightDir, normal);
        float spec = pow(max(dot(viewDir, reflectDir), 0.0), materialShininess);
        vec3 specular = materialSpecular * globalSpecularLevel * spec * lightColor[i];

        color += (diffuse + specular) * lightIntensity[i] * attenuation * spotFactor;
    }

    FragColor = vec4(color, 1.0);
}
"""


class ShaderProgram:
    def __init__(self, vertex_source, fragment_source):
        vertex = self._compile(GL_VERTEX_SHADER, vertex_source)
        fragment = self._compile(GL_FRAGMENT_SHADER, fragment_source)
        self.program = glCreateProgram()
        glAttachShader(self.program, vertex)
        glAttachShader(self.program, fragment)
        glLinkProgram(self.program)
        self._check_program(self.program)
        glDeleteShader(vertex)
        glDeleteShader(fragment)

    def use(self):
        glUseProgram(self.program)

    def uniform(self, name):
        return glGetUniformLocation(self.program, name)

    @staticmethod
    def _compile(shader_type, source):
        shader = glCreateShader(shader_type)
        glShaderSource(shader, source)
        glCompileShader(shader)
        ok = glGetShaderiv(shader, GL_COMPILE_STATUS)
        if not ok:
            log = glGetShaderInfoLog(shader).decode("utf-8", errors="replace")
            raise RuntimeError(f"Erro ao compilar shader:\n{log}")
        return shader

    @staticmethod
    def _check_program(program):
        ok = glGetProgramiv(program, GL_LINK_STATUS)
        if not ok:
            log = glGetProgramInfoLog(program).decode("utf-8", errors="replace")
            raise RuntimeError(f"Erro ao linkar programa:\n{log}")
'''


markdown_loader = """
## 3. Carregador OBJ com suporte a normais

O parser abaixo le apenas a geometria necessaria dos arquivos `.obj`:

- `v`, `vt`, `vn` e `f`;
- `usemtl` apenas para separar submalhas, quando um `.obj` precisa de mais de uma textura manual;
- faces sem normal, caso em que calculamos uma normal por triangulo.

As texturas sao escolhidas manualmente em um catalogo Python por nome de malha ou submalha, sem ler `.mtl`.
"""


code_loader = r'''
@dataclass
class MeshSegment:
    start: int
    count: int
    material_name: str
    texture_path: Path | None


@dataclass
class CpuMesh:
    name: str
    vertex_data: np.ndarray
    segments: list[MeshSegment]


@dataclass
class GpuMesh:
    name: str
    vao: int
    vbo: int
    segments: list[dict]
    vertex_count: int


def resolve_obj_index(index_text, total):
    index = int(index_text)
    return index - 1 if index > 0 else total + index


def compute_face_normal(p0, p1, p2):
    edge1 = np.array(p1, dtype=np.float32) - np.array(p0, dtype=np.float32)
    edge2 = np.array(p2, dtype=np.float32) - np.array(p0, dtype=np.float32)
    normal = np.cross(edge1, edge2)
    length = np.linalg.norm(normal)
    if length < 1e-8:
        return (0.0, 1.0, 0.0)
    normal /= length
    return tuple(float(value) for value in normal)


def load_obj_mesh(obj_path):
    obj_path = Path(obj_path)
    positions = []
    texcoords = []
    normals = []
    out_positions = []
    out_texcoords = []
    out_normals = []
    segments = []
    current_material = "__default__"
    active_material = None
    active_start = 0
    submesh_textures = MODEL_SUBMESH_TEXTURES.get(obj_path.stem, {})
    default_texture = MODEL_TEXTURES.get(obj_path.stem)

    def texture_for_material(material_name):
        return submesh_textures.get(material_name, default_texture)

    def close_segment():
        nonlocal active_material, active_start
        end = len(out_positions)
        if active_material is not None and end > active_start:
            segments.append(
                MeshSegment(
                    start=active_start,
                    count=end - active_start,
                    material_name=active_material,
                    texture_path=texture_for_material(active_material),
                )
            )
        active_material = None
        active_start = end

    def use_material(material_name):
        nonlocal active_material, active_start
        if active_material != material_name:
            close_segment()
            active_material = material_name
            active_start = len(out_positions)

    for raw_line in obj_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        command = parts[0]

        if command == "v":
            positions.append(tuple(map(float, parts[1:4])))
        elif command == "vt":
            texcoords.append(tuple(map(float, parts[1:3])))
        elif command == "vn":
            normals.append(tuple(map(float, parts[1:4])))
        elif command == "usemtl":
            current_material = " ".join(parts[1:]) if len(parts) > 1 else "__default__"
        elif command == "f":
            use_material(current_material)
            polygon = []
            for token in parts[1:]:
                values = token.split("/")
                vi = resolve_obj_index(values[0], len(positions))
                ti = resolve_obj_index(values[1], len(texcoords)) if len(values) > 1 and values[1] else None
                ni = resolve_obj_index(values[2], len(normals)) if len(values) > 2 and values[2] else None
                polygon.append((vi, ti, ni))

            for i in range(1, len(polygon) - 1):
                triangle = (polygon[0], polygon[i], polygon[i + 1])
                p0 = positions[triangle[0][0]]
                p1 = positions[triangle[1][0]]
                p2 = positions[triangle[2][0]]
                fallback_normal = compute_face_normal(p0, p1, p2)
                for vi, ti, ni in triangle:
                    out_positions.append(positions[vi])
                    out_texcoords.append(texcoords[ti] if ti is not None else (0.0, 0.0))
                    out_normals.append(normals[ni] if ni is not None else fallback_normal)
    close_segment()

    if not segments:
        segments = [
            MeshSegment(
                start=0,
                count=len(out_positions),
                material_name="__default__",
                texture_path=default_texture,
            )
        ]

    vertex_data = np.zeros(
        len(out_positions),
        dtype=[("position", np.float32, 3), ("texcoord", np.float32, 2), ("normal", np.float32, 3)],
    )
    vertex_data["position"] = out_positions
    vertex_data["texcoord"] = out_texcoords
    vertex_data["normal"] = out_normals
    return CpuMesh(obj_path.stem, vertex_data, segments)


def build_quad_mesh(name, quads, texture_path):
    positions = []
    texcoords = []
    normals = []

    for quad in quads:
        p0, p1, p2, p3, uv_scale = quad
        normal = compute_face_normal(p0, p1, p2)
        uv0 = (0.0, 0.0)
        uv1 = (uv_scale[0], 0.0)
        uv2 = (uv_scale[0], uv_scale[1])
        uv3 = (0.0, uv_scale[1])
        triangles = [
            (p0, uv0, normal),
            (p1, uv1, normal),
            (p2, uv2, normal),
            (p0, uv0, normal),
            (p2, uv2, normal),
            (p3, uv3, normal),
        ]
        for position, uv, tri_normal in triangles:
            positions.append(position)
            texcoords.append(uv)
            normals.append(tri_normal)

    vertex_data = np.zeros(
        len(positions),
        dtype=[("position", np.float32, 3), ("texcoord", np.float32, 2), ("normal", np.float32, 3)],
    )
    vertex_data["position"] = positions
    vertex_data["texcoord"] = texcoords
    vertex_data["normal"] = normals
    return CpuMesh(
        name,
        vertex_data,
        [MeshSegment(start=0, count=len(positions), material_name="__default__", texture_path=texture_path)],
    )
'''


markdown_scene = """
## 4. Cena, materiais e luzes do Projeto 3

Mantivemos a balada urbana, mas agora cada instancia recebe parametros de material no proprio codigo. O mapeamento foi organizado assim:

- `INTERIOR`: sala do clube, pista, sofas, cadeiras, pessoas internas, boombox, luminarias e bola de discoteca;
- `EXTERIOR`: estacionamento, carro, lixeira, postes e pessoas externas;
- `SHARED`: objetos de transicao, como a porta metalica, que podem receber luz dos dois lados;
- o skybox e desenhado separadamente sem participar da iluminacao.

As fontes de luz sao:

1. **Dois farois externos** associados ao carro translacionavel e controlados pelo mesmo interruptor da luz externa.
2. **Luz interna quente** em uma luminaria de teto.
3. **Luz interna fria** na bola de discoteca.

Cada uma tem interruptor independente. A luz ambiente tambem pode ser ligada/desligada separadamente e ajustada por teclado.
"""


code_scene = r'''
SCENE_CATALOG = {
    "ambiente": [
        "club_room",
        "lounge_floor",
        "dance_floor",
        "club_front_facade",
        "parking_lot",
        "night_skybox",
    ],
    "interno": [
        "party_person_01",
        "party_person_male_01",
        "boombox",
        "bar_chair_round_01",
        "sofa_01",
        "modern_ceiling_lamp_01",
        "disco_ball",
        "disco_support",
    ],
    "externo": [
        "rollershutter_door",
        "corrado_car_01",
        "street_lamp_01",
        "oga_trash_can_01",
        "party_person_01",
        "party_person_male_01",
    ],
}

for group, names in SCENE_CATALOG.items():
    print(f"{group}:")
    for model_name in names:
        if model_name == "club_front_facade":
            mesh = build_quad_mesh(
                "club_front_facade",
                [
                    ((-10.0, 0.0, 7.53), (-2.1, 0.0, 7.53), (-2.1, 5.4, 7.53), (-10.0, 5.4, 7.53), (4.0, 2.0)),
                    ((2.1, 0.0, 7.53), (10.0, 0.0, 7.53), (10.0, 5.4, 7.53), (2.1, 5.4, 7.53), (4.0, 2.0)),
                    ((-2.1, 2.7, 7.53), (2.1, 2.7, 7.53), (2.1, 5.4, 7.53), (-2.1, 5.4, 7.53), (2.0, 1.5)),
                ],
                TEXTURES_DIR / "club_wall_black_painted_planks_diff_1k.jpg",
            )
        else:
            mesh = load_obj_mesh(MODELS_DIR / f"{model_name}.obj")
        textured_segments = sum(1 for segment in mesh.segments if segment.texture_path is not None)
        print(
            f"  - {model_name:36s} | vertices: {len(mesh.vertex_data):7d} "
            f"| segmentos texturizados: {textured_segments:2d}/{len(mesh.segments):2d}"
        )


WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 720

if not glfw.init():
    raise RuntimeError("Nao foi possivel inicializar GLFW.")

glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)

window = glfw.create_window(WINDOW_WIDTH, WINDOW_HEIGHT, "Projeto 3 - Balada urbana iluminada", None, None)
if window is None:
    glfw.terminate()
    raise RuntimeError("Nao foi possivel criar a janela GLFW.")

glfw.make_context_current(window)
glfw.swap_interval(1)
glViewport(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT)

glEnable(GL_DEPTH_TEST)
glDisable(GL_CULL_FACE)

shader = ShaderProgram(VERTEX_SHADER_SOURCE, FRAGMENT_SHADER_SOURCE)
shader.use()
glUniform1i(shader.uniform("imageTexture"), 0)

texture_cache = {}
white_texture_id = None


def load_texture(texture_path):
    texture_path = Path(texture_path).resolve()
    if texture_path in texture_cache:
        return texture_cache[texture_path]

    image = Image.open(texture_path).transpose(Image.FLIP_TOP_BOTTOM).convert("RGBA")
    width, height = image.size
    pixels = image.tobytes()

    texture_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, pixels)
    glGenerateMipmap(GL_TEXTURE_2D)

    texture_cache[texture_path] = texture_id
    return texture_id


def get_white_texture():
    global white_texture_id
    if white_texture_id is not None:
        return white_texture_id

    texture_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    white_pixel = bytes([255, 255, 255, 255])
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 1, 1, 0, GL_RGBA, GL_UNSIGNED_BYTE, white_pixel)
    white_texture_id = texture_id
    return texture_id


def upload_mesh(cpu_mesh):
    vao = glGenVertexArrays(1)
    vbo = glGenBuffers(1)

    glBindVertexArray(vao)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, cpu_mesh.vertex_data.nbytes, cpu_mesh.vertex_data, GL_STATIC_DRAW)

    stride = cpu_mesh.vertex_data.strides[0]
    pos_offset = ctypes.c_void_p(cpu_mesh.vertex_data.dtype.fields["position"][1])
    uv_offset = ctypes.c_void_p(cpu_mesh.vertex_data.dtype.fields["texcoord"][1])
    normal_offset = ctypes.c_void_p(cpu_mesh.vertex_data.dtype.fields["normal"][1])

    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, pos_offset)
    glEnableVertexAttribArray(1)
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, stride, uv_offset)
    glEnableVertexAttribArray(2)
    glVertexAttribPointer(2, 3, GL_FLOAT, GL_FALSE, stride, normal_offset)

    gpu_segments = []
    for segment in cpu_mesh.segments:
        gpu_segments.append(
            {
                "start": segment.start,
                "count": segment.count,
                "texture_id": load_texture(segment.texture_path) if segment.texture_path else get_white_texture(),
            }
        )

    glBindVertexArray(0)
    return GpuMesh(cpu_mesh.name, vao, vbo, gpu_segments, len(cpu_mesh.vertex_data))


all_model_names = list(dict.fromkeys(SCENE_CATALOG["ambiente"] + SCENE_CATALOG["interno"] + SCENE_CATALOG["externo"]))
gpu_meshes = {}
for model_name in all_model_names:
    if model_name == "club_front_facade":
        cpu_mesh = build_quad_mesh(
            "club_front_facade",
            [
                ((-10.0, 0.0, 7.53), (-2.1, 0.0, 7.53), (-2.1, 5.4, 7.53), (-10.0, 5.4, 7.53), (4.0, 2.0)),
                ((2.1, 0.0, 7.53), (10.0, 0.0, 7.53), (10.0, 5.4, 7.53), (2.1, 5.4, 7.53), (4.0, 2.0)),
                ((-2.1, 2.7, 7.53), (2.1, 2.7, 7.53), (2.1, 5.4, 7.53), (-2.1, 5.4, 7.53), (2.0, 1.5)),
            ],
            TEXTURES_DIR / "club_wall_black_painted_planks_diff_1k.jpg",
        )
    else:
        cpu_mesh = load_obj_mesh(MODELS_DIR / f"{model_name}.obj")
    gpu_meshes[model_name] = upload_mesh(cpu_mesh)

print("Modelos enviados para a GPU:", ", ".join(gpu_meshes.keys()))


camera_pos = glm.vec3(0.0, 1.7, 9.5)
camera_front = glm.normalize(glm.vec3(0.0, -0.10, -1.0))
camera_up = glm.vec3(0.0, 1.0, 0.0)

yaw = -90.0
pitch = -7.0
last_x = WINDOW_WIDTH / 2
last_y = WINDOW_HEIGHT / 2
first_mouse = True
fov = 45.0

show_wireframe = False
car_translation = 0.0
ambient_enabled = True
ambient_level = 0.30
global_diffuse_level = 1.00
global_specular_level = 0.75

light_states = {
    "external_car": True,
    "internal_lamp": True,
    "internal_disco": True,
}

SCENE_LIMIT_X = 17.5
SCENE_MIN_Z = -10.0
SCENE_MAX_Z = 31.0
MIN_CAMERA_Y = 0.35
MAX_CAMERA_Y = 9.0


def clamp(value, lower, upper):
    return max(lower, min(upper, value))


def clamp_camera_position():
    global camera_pos
    camera_pos.x = clamp(camera_pos.x, -SCENE_LIMIT_X, SCENE_LIMIT_X)
    camera_pos.y = clamp(camera_pos.y, MIN_CAMERA_Y, MAX_CAMERA_Y)
    camera_pos.z = clamp(camera_pos.z, SCENE_MIN_Z, SCENE_MAX_Z)


def print_lighting_status():
    print(
        "Luzes => ambiente:",
        "ligada" if ambient_enabled else "desligada",
        "| externa:",
        "ligada" if light_states["external_car"] else "desligada",
        "| interna teto:",
        "ligada" if light_states["internal_lamp"] else "desligada",
        "| interna disco:",
        "ligada" if light_states["internal_disco"] else "desligada",
        f"| ka={ambient_level:.2f} kd={global_diffuse_level:.2f} ks={global_specular_level:.2f}",
    )


def key_callback(active_window, key, scancode, action, mods):
    global show_wireframe, ambient_enabled, ambient_level, global_diffuse_level, global_specular_level
    _ = scancode, mods

    if action != glfw.PRESS:
        return

    if key == glfw.KEY_ESCAPE:
        glfw.set_window_should_close(active_window, True)
    elif key == glfw.KEY_P:
        show_wireframe = not show_wireframe
        print("Malha poligonal:", "visivel" if show_wireframe else "oculta")
    elif key == glfw.KEY_0:
        ambient_enabled = not ambient_enabled
        print_lighting_status()
    elif key == glfw.KEY_1:
        light_states["external_car"] = not light_states["external_car"]
        print_lighting_status()
    elif key == glfw.KEY_2:
        light_states["internal_lamp"] = not light_states["internal_lamp"]
        print_lighting_status()
    elif key == glfw.KEY_3:
        light_states["internal_disco"] = not light_states["internal_disco"]
        print_lighting_status()
    elif key == glfw.KEY_U:
        ambient_level = clamp(ambient_level + 0.05, 0.0, 1.0)
        print_lighting_status()
    elif key == glfw.KEY_J:
        ambient_level = clamp(ambient_level - 0.05, 0.0, 1.0)
        print_lighting_status()
    elif key == glfw.KEY_I:
        global_diffuse_level = clamp(global_diffuse_level + 0.05, 0.0, 2.0)
        print_lighting_status()
    elif key == glfw.KEY_K:
        global_diffuse_level = clamp(global_diffuse_level - 0.05, 0.0, 2.0)
        print_lighting_status()
    elif key == glfw.KEY_O:
        global_specular_level = clamp(global_specular_level + 0.05, 0.0, 2.0)
        print_lighting_status()
    elif key == glfw.KEY_L:
        global_specular_level = clamp(global_specular_level - 0.05, 0.0, 2.0)
        print_lighting_status()


def mouse_callback(_window, xpos, ypos):
    global yaw, pitch, last_x, last_y, first_mouse, camera_front
    if first_mouse:
        last_x = xpos
        last_y = ypos
        first_mouse = False

    xoffset = xpos - last_x
    yoffset = last_y - ypos
    last_x = xpos
    last_y = ypos

    sensitivity = 0.08
    yaw += xoffset * sensitivity
    pitch += yoffset * sensitivity
    pitch = clamp(pitch, -89.0, 89.0)

    direction = glm.vec3(
        math.cos(math.radians(yaw)) * math.cos(math.radians(pitch)),
        math.sin(math.radians(pitch)),
        math.sin(math.radians(yaw)) * math.cos(math.radians(pitch)),
    )
    camera_front = glm.normalize(direction)


def framebuffer_size_callback(_window, width, height):
    global WINDOW_WIDTH, WINDOW_HEIGHT
    WINDOW_WIDTH = max(1, width)
    WINDOW_HEIGHT = max(1, height)
    glViewport(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT)


def process_input(delta_time):
    global camera_pos, car_translation

    speed = 5.5 if glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS else 3.2
    distance = speed * delta_time
    front_flat = glm.vec3(camera_front.x, 0.0, camera_front.z)
    if glm.length(front_flat) < 0.001:
        front_flat = glm.vec3(0.0, 0.0, -1.0)
    front_flat = glm.normalize(front_flat)
    right = glm.normalize(glm.cross(front_flat, camera_up))

    if glfw.get_key(window, glfw.KEY_W) == glfw.PRESS:
        camera_pos += front_flat * distance
    if glfw.get_key(window, glfw.KEY_S) == glfw.PRESS:
        camera_pos -= front_flat * distance
    if glfw.get_key(window, glfw.KEY_D) == glfw.PRESS:
        camera_pos += right * distance
    if glfw.get_key(window, glfw.KEY_A) == glfw.PRESS:
        camera_pos -= right * distance
    if glfw.get_key(window, glfw.KEY_SPACE) == glfw.PRESS:
        camera_pos += camera_up * distance
    if glfw.get_key(window, glfw.KEY_C) == glfw.PRESS:
        camera_pos -= camera_up * distance

    if glfw.get_key(window, glfw.KEY_T) == glfw.PRESS:
        car_translation = clamp(car_translation + 3.0 * delta_time, -7.0, 7.0)
    if glfw.get_key(window, glfw.KEY_G) == glfw.PRESS:
        car_translation = clamp(car_translation - 3.0 * delta_time, -7.0, 7.0)

    clamp_camera_position()


glfw.set_key_callback(window, key_callback)
glfw.set_cursor_pos_callback(window, mouse_callback)
glfw.set_framebuffer_size_callback(window, framebuffer_size_callback)
glfw.set_input_mode(window, glfw.CURSOR, glfw.CURSOR_DISABLED)


def vec3_tuple(values):
    return glm.vec3(float(values[0]), float(values[1]), float(values[2]))


def material_profile(mesh_name, zone):
    interior = {
        "club_room": (0.52, 0.84, 0.18, 12.0),
        "lounge_floor": (0.34, 0.90, 0.14, 10.0),
        "dance_floor": (0.38, 0.96, 0.34, 26.0),
        "party_person_01": (0.34, 0.78, 0.22, 18.0),
        "party_person_male_01": (0.32, 0.76, 0.22, 18.0),
        "boombox": (0.22, 0.70, 0.70, 52.0),
        "bar_chair_round_01": (0.20, 0.68, 0.40, 30.0),
        "sofa_01": (0.24, 0.66, 0.16, 12.0),
        "modern_ceiling_lamp_01": (0.40, 0.60, 0.55, 40.0),
        "disco_ball": (0.20, 0.75, 0.95, 96.0),
        "disco_support": (0.20, 0.65, 0.65, 44.0),
    }
    exterior = {
        "parking_lot": (0.34, 0.78, 0.08, 8.0),
        "rollershutter_door": (0.34, 0.72, 0.48, 34.0),
        "corrado_car_01": (0.28, 0.78, 0.90, 72.0),
        "oga_trash_can_01": (0.28, 0.68, 0.45, 28.0),
        "street_lamp_01": (0.30, 0.70, 0.55, 38.0),
        "party_person_01": (0.30, 0.70, 0.18, 16.0),
        "party_person_male_01": (0.30, 0.70, 0.18, 16.0),
    }
    neutral = {
        "night_skybox": (0.0, 0.0, 0.0, 1.0),
    }

    if zone == ZONE_INTERIOR:
        values = interior.get(mesh_name, (0.22, 0.70, 0.30, 24.0))
    elif zone == ZONE_EXTERIOR:
        values = exterior.get(mesh_name, (0.18, 0.72, 0.30, 24.0))
    else:
        values = neutral.get(mesh_name, (0.0, 0.0, 0.0, 1.0))

    return {
        "ambient_factor": values[0],
        "diffuse_factor": values[1],
        "specular_factor": values[2],
        "shininess": values[3],
        "base_color": (1.0, 1.0, 1.0),
        "emissive_color": (0.0, 0.0, 0.0),
        "emissive_strength": 0.0,
    }


def node(mesh, position=(0, 0, 0), scale=(1, 1, 1), rotations=None, zone=ZONE_INTERIOR, material=None):
    return {
        "mesh": mesh,
        "position": vec3_tuple(position),
        "scale": vec3_tuple(scale),
        "rotations": rotations or [],
        "zone": zone,
        "material": material or material_profile(mesh, zone),
    }


def merge_material(base_material, **overrides):
    merged = dict(base_material)
    merged.update(overrides)
    return merged


def car_attached_node(mesh, offset=(0, 0, 0), scale=(1, 1, 1), rotations=None, zone=ZONE_EXTERIOR, material=None):
    scene_node = node(mesh, position=offset, scale=scale, rotations=rotations, zone=zone, material=material)
    scene_node["attach_to_car"] = True
    return scene_node


scene_nodes = [
    node("parking_lot", position=(0.0, -0.03, 18.0), zone=ZONE_EXTERIOR),
    node(
        "rollershutter_door",
        position=(-1.85, 0.02, 7.62),
        scale=(1.85, 1.55, 1.55),
        zone=ZONE_SHARED,
        material=material_profile("rollershutter_door", ZONE_EXTERIOR),
    ),
    node(
        "club_front_facade",
        zone=ZONE_SHARED,
        material=merge_material(
            material_profile("club_room", ZONE_EXTERIOR),
            ambient_factor=0.36,
            diffuse_factor=0.80,
            specular_factor=0.12,
            shininess=10.0,
        ),
    ),
    node("club_room", zone=ZONE_INTERIOR),
    node("lounge_floor", position=(0.0, 0.005, 0.0), zone=ZONE_INTERIOR),
    node("dance_floor", position=(0.0, 0.02, 0.0), zone=ZONE_INTERIOR),

    node("party_person_01", position=(-2.1, 0.02, -0.8), scale=(0.92, 0.92, 0.92), rotations=[(188, (0, 1, 0))], zone=ZONE_INTERIOR),
    node("party_person_01", position=(1.8, 0.02, -0.5), scale=(0.90, 0.90, 0.90), rotations=[(170, (0, 1, 0))], zone=ZONE_INTERIOR),
    node("party_person_01", position=(0.7, 0.02, 1.2), scale=(0.91, 0.91, 0.91), rotations=[(176, (0, 1, 0))], zone=ZONE_INTERIOR),
    node("party_person_01", position=(-1.4, 0.02, -2.0), scale=(0.89, 0.89, 0.89), rotations=[(194, (0, 1, 0))], zone=ZONE_INTERIOR),
    node("party_person_01", position=(-5.6, 0.02, 3.8), scale=(0.88, 0.88, 0.88), rotations=[(-18, (0, 1, 0))], zone=ZONE_INTERIOR),
    node("party_person_01", position=(5.5, 0.02, 3.7), scale=(0.88, 0.88, 0.88), rotations=[(22, (0, 1, 0))], zone=ZONE_INTERIOR),
    node("party_person_01", position=(-6.9, 0.02, 1.3), scale=(0.86, 0.86, 0.86), rotations=[(-8, (0, 1, 0))], zone=ZONE_INTERIOR),
    node("party_person_01", position=(6.8, 0.02, 1.4), scale=(0.87, 0.87, 0.87), rotations=[(10, (0, 1, 0))], zone=ZONE_INTERIOR),
    node("party_person_01", position=(-3.4, 0.02, 4.8), scale=(0.87, 0.87, 0.87), rotations=[(146, (0, 1, 0))], zone=ZONE_INTERIOR),
    node("party_person_01", position=(3.5, 0.02, 4.9), scale=(0.87, 0.87, 0.87), rotations=[(-142, (0, 1, 0))], zone=ZONE_INTERIOR),

    node("party_person_male_01", position=(-0.6, 0.02, 0.6), scale=(0.96, 0.96, 0.96), rotations=[(4, (0, 1, 0))], zone=ZONE_INTERIOR),
    node("party_person_male_01", position=(-0.2, 0.02, -1.3), scale=(0.97, 0.97, 0.97), rotations=[(6, (0, 1, 0))], zone=ZONE_INTERIOR),
    node("party_person_male_01", position=(2.6, 0.02, -1.0), scale=(0.94, 0.94, 0.94), rotations=[(-14, (0, 1, 0))], zone=ZONE_INTERIOR),
    node("party_person_male_01", position=(1.5, 0.02, -2.5), scale=(0.95, 0.95, 0.95), rotations=[(-6, (0, 1, 0))], zone=ZONE_INTERIOR),
    node("party_person_male_01", position=(-4.8, 0.02, 2.7), scale=(0.92, 0.92, 0.92), rotations=[(34, (0, 1, 0))], zone=ZONE_INTERIOR),
    node("party_person_male_01", position=(4.9, 0.02, 2.8), scale=(0.92, 0.92, 0.92), rotations=[(-32, (0, 1, 0))], zone=ZONE_INTERIOR),
    node("party_person_male_01", position=(-4.9, 0.02, 5.1), scale=(0.90, 0.90, 0.90), rotations=[(40, (0, 1, 0))], zone=ZONE_INTERIOR),
    node("party_person_male_01", position=(5.0, 0.02, 5.0), scale=(0.90, 0.90, 0.90), rotations=[(-38, (0, 1, 0))], zone=ZONE_INTERIOR),

    node("boombox", position=(0.0, 0.02, -5.8), scale=(4.15, 4.15, 4.15), zone=ZONE_INTERIOR),

    node("sofa_01", position=(-8.55, 0.02, 4.5), scale=(2.1, 2.1, 2.1), rotations=[(90, (0, 1, 0))], zone=ZONE_INTERIOR),
    node("sofa_01", position=(8.55, 0.02, 4.5), scale=(2.1, 2.1, 2.1), rotations=[(-90, (0, 1, 0))], zone=ZONE_INTERIOR),
    node("bar_chair_round_01", position=(-8.7, 0.02, 1.9), scale=(1.26, 1.26, 1.26), rotations=[(90, (0, 1, 0))], zone=ZONE_INTERIOR),
    node("bar_chair_round_01", position=(-8.7, 0.02, 7.05), scale=(1.26, 1.26, 1.26), rotations=[(90, (0, 1, 0))], zone=ZONE_INTERIOR),
    node("bar_chair_round_01", position=(8.7, 0.02, 1.9), scale=(1.26, 1.26, 1.26), rotations=[(-90, (0, 1, 0))], zone=ZONE_INTERIOR),
    node("bar_chair_round_01", position=(8.7, 0.02, 7.05), scale=(1.26, 1.26, 1.26), rotations=[(-90, (0, 1, 0))], zone=ZONE_INTERIOR),

    node("modern_ceiling_lamp_01", position=(-6.5, 3.75, -1.4), scale=(1.45, 1.45, 1.45), zone=ZONE_INTERIOR),
    node(
        "modern_ceiling_lamp_01",
        position=(-2.2, 3.75, -1.4),
        scale=(1.45, 1.45, 1.45),
        zone=ZONE_INTERIOR,
        material=merge_material(
            material_profile("modern_ceiling_lamp_01", ZONE_INTERIOR),
            emissive_color=(1.0, 0.78, 0.45),
            emissive_strength=0.95,
            emissive_toggle="internal_lamp",
        ),
    ),
    node("modern_ceiling_lamp_01", position=(2.2, 3.75, -1.4), scale=(1.45, 1.45, 1.45), zone=ZONE_INTERIOR),
    node("modern_ceiling_lamp_01", position=(6.5, 3.75, -1.4), scale=(1.45, 1.45, 1.45), zone=ZONE_INTERIOR),
    node("modern_ceiling_lamp_01", position=(-4.2, 3.75, 2.4), scale=(1.3, 1.3, 1.3), zone=ZONE_INTERIOR),
    node("modern_ceiling_lamp_01", position=(0.0, 3.75, 2.4), scale=(1.3, 1.3, 1.3), zone=ZONE_INTERIOR),
    node("modern_ceiling_lamp_01", position=(4.2, 3.75, 2.4), scale=(1.3, 1.3, 1.3), zone=ZONE_INTERIOR),
    node("disco_support", position=(0.0, 4.15, -0.3), scale=(1.02, 1.25, 1.02), zone=ZONE_INTERIOR),
    node(
        "disco_ball",
        position=(0.0, 3.68, -0.3),
        scale=(0.84, 0.84, 0.84),
        zone=ZONE_INTERIOR,
        material=merge_material(
            material_profile("disco_ball", ZONE_INTERIOR),
            emissive_color=(0.22, 0.82, 1.0),
            emissive_strength=0.72,
            emissive_toggle="internal_disco",
        ),
    ),

    node("corrado_car_01", position=(11.8, 0.03, 14.9), scale=(0.0092, 0.0092, 0.0092), zone=ZONE_EXTERIOR),
    car_attached_node(
        "disco_ball",
        offset=(10.22, 0.58, 14.18),
        scale=(0.06, 0.06, 0.06),
        zone=ZONE_EXTERIOR,
        material=merge_material(
            material_profile("disco_ball", ZONE_EXTERIOR),
            base_color=(1.0, 0.96, 0.84),
            ambient_factor=0.0,
            diffuse_factor=0.0,
            specular_factor=0.0,
            shininess=4.0,
            emissive_color=(1.0, 0.96, 0.84),
            emissive_strength=2.6,
            emissive_toggle="external_car",
        ),
    ),
    car_attached_node(
        "disco_ball",
        offset=(10.22, 0.58, 15.62),
        scale=(0.06, 0.06, 0.06),
        zone=ZONE_EXTERIOR,
        material=merge_material(
            material_profile("disco_ball", ZONE_EXTERIOR),
            base_color=(1.0, 0.96, 0.84),
            ambient_factor=0.0,
            diffuse_factor=0.0,
            specular_factor=0.0,
            shininess=4.0,
            emissive_color=(1.0, 0.96, 0.84),
            emissive_strength=2.6,
            emissive_toggle="external_car",
        ),
    ),
    node("oga_trash_can_01", position=(-8.95, 0.03, 8.05), scale=(0.34, 0.34, 0.34), rotations=[(180, (0, 1, 0))], zone=ZONE_EXTERIOR),

    node("party_person_01", position=(-5.2, 0.03, 12.8), scale=(0.82, 0.82, 0.82), rotations=[(30, (0, 1, 0))], zone=ZONE_EXTERIOR),
    node("party_person_male_01", position=(-2.3, 0.03, 16.3), scale=(0.88, 0.88, 0.88), rotations=[(72, (0, 1, 0))], zone=ZONE_EXTERIOR),
    node("party_person_01", position=(2.6, 0.03, 18.7), scale=(0.80, 0.80, 0.80), rotations=[(-36, (0, 1, 0))], zone=ZONE_EXTERIOR),
    node("party_person_male_01", position=(8.8, 0.03, 19.6), scale=(0.84, 0.84, 0.84), rotations=[(-120, (0, 1, 0))], zone=ZONE_EXTERIOR),
    node("party_person_01", position=(-11.8, 0.03, 20.8), scale=(0.78, 0.78, 0.78), rotations=[(118, (0, 1, 0))], zone=ZONE_EXTERIOR),
    node("party_person_male_01", position=(12.0, 0.03, 22.1), scale=(0.82, 0.82, 0.82), rotations=[(-122, (0, 1, 0))], zone=ZONE_EXTERIOR),

    node("street_lamp_01", position=(-16.0, 0.03, 10.5), scale=(1.38, 1.38, 1.38), zone=ZONE_EXTERIOR),
    node("street_lamp_01", position=(-16.0, 0.03, 17.5), scale=(1.38, 1.38, 1.38), zone=ZONE_EXTERIOR),
    node("street_lamp_01", position=(-16.0, 0.03, 24.5), scale=(1.38, 1.38, 1.38), zone=ZONE_EXTERIOR),
    node("street_lamp_01", position=(16.0, 0.03, 10.5), scale=(1.38, 1.38, 1.38), zone=ZONE_EXTERIOR),
    node("street_lamp_01", position=(16.0, 0.03, 17.5), scale=(1.38, 1.38, 1.38), zone=ZONE_EXTERIOR),
    node("street_lamp_01", position=(16.0, 0.03, 24.5), scale=(1.38, 1.38, 1.38), zone=ZONE_EXTERIOR),
]


def build_model_matrix(scene_node):
    model = glm.mat4(1.0)
    position = glm.vec3(scene_node["position"])
    scale = glm.vec3(scene_node["scale"])

    if scene_node["mesh"] == "corrado_car_01" or scene_node.get("attach_to_car"):
        position += glm.vec3(car_translation, 0.0, 0.0)

    model = glm.translate(model, position)

    for angle_degrees, axis in scene_node["rotations"]:
        model = glm.rotate(model, glm.radians(angle_degrees), vec3_tuple(axis))

    model = glm.scale(model, scale)
    return model


def view_matrix():
    return glm.lookAt(camera_pos, camera_pos + camera_front, camera_up)


def projection_matrix():
    aspect = WINDOW_WIDTH / WINDOW_HEIGHT
    return glm.perspective(glm.radians(fov), aspect, 0.1, 120.0)


loc_model = shader.uniform("model")
loc_view = shader.uniform("view")
loc_projection = shader.uniform("projection")
loc_normal_matrix = shader.uniform("normalMatrix")
loc_view_pos = shader.uniform("viewPos")
loc_unlit = shader.uniform("unlit")
loc_base_color = shader.uniform("baseColor")
loc_emissive_color = shader.uniform("emissiveColor")
loc_emissive_strength = shader.uniform("emissiveStrength")
loc_ambient_enabled = shader.uniform("ambientEnabled")
loc_ambient_level = shader.uniform("ambientLevel")
loc_object_zone = shader.uniform("objectZone")
loc_global_diffuse = shader.uniform("globalDiffuseLevel")
loc_global_specular = shader.uniform("globalSpecularLevel")
loc_material_ambient = shader.uniform("materialAmbient")
loc_material_diffuse = shader.uniform("materialDiffuse")
loc_material_specular = shader.uniform("materialSpecular")
loc_material_shininess = shader.uniform("materialShininess")
loc_light_pos = [shader.uniform(f"lightPos[{i}]") for i in range(MAX_LIGHTS)]
loc_light_color = [shader.uniform(f"lightColor[{i}]") for i in range(MAX_LIGHTS)]
loc_light_intensity = [shader.uniform(f"lightIntensity[{i}]") for i in range(MAX_LIGHTS)]
loc_light_enabled = [shader.uniform(f"lightEnabled[{i}]") for i in range(MAX_LIGHTS)]
loc_light_zone = [shader.uniform(f"lightZone[{i}]") for i in range(MAX_LIGHTS)]
loc_light_is_spot = [shader.uniform(f"lightIsSpot[{i}]") for i in range(MAX_LIGHTS)]
loc_light_direction = [shader.uniform(f"lightDirection[{i}]") for i in range(MAX_LIGHTS)]
loc_light_cutoff_cos = [shader.uniform(f"lightCutoffCos[{i}]") for i in range(MAX_LIGHTS)]


def send_matrix(location, matrix):
    glUniformMatrix4fv(location, 1, GL_FALSE, glm.value_ptr(matrix))


def send_normal_matrix(model):
    normal_matrix = glm.mat3(glm.transpose(glm.inverse(model)))
    glUniformMatrix3fv(loc_normal_matrix, 1, GL_FALSE, glm.value_ptr(normal_matrix))


def set_material(material, zone):
    emissive_strength = material.get("emissive_strength", 0.0)
    toggle_name = material.get("emissive_toggle")
    if toggle_name is not None and not light_states.get(toggle_name, False):
        emissive_strength = 0.0

    glUniform1i(loc_object_zone, zone)
    glUniform3f(loc_base_color, *material["base_color"])
    glUniform3f(loc_emissive_color, *material.get("emissive_color", (0.0, 0.0, 0.0)))
    glUniform1f(loc_emissive_strength, emissive_strength)
    glUniform1f(loc_material_ambient, material["ambient_factor"])
    glUniform1f(loc_material_diffuse, material["diffuse_factor"])
    glUniform1f(loc_material_specular, material["specular_factor"])
    glUniform1f(loc_material_shininess, material["shininess"])


def current_lights():
    return [
        {
            "position": (10.22 + car_translation, 0.58, 14.18),
            "color": (1.00, 0.96, 0.80),
            "intensity": 4.10,
            "enabled": light_states["external_car"],
            "zone": ZONE_EXTERIOR,
            "is_spot": True,
            "direction": (-1.0, -0.08, -0.05),
            "cutoff_cos": 0.90,
        },
        {
            "position": (10.22 + car_translation, 0.58, 15.62),
            "color": (1.00, 0.96, 0.80),
            "intensity": 4.10,
            "enabled": light_states["external_car"],
            "zone": ZONE_EXTERIOR,
            "is_spot": True,
            "direction": (-1.0, -0.08, 0.05),
            "cutoff_cos": 0.90,
        },
        {
            "position": (-2.2, 3.45, -1.4),
            "color": (1.00, 0.66, 0.30),
            "intensity": 2.90,
            "enabled": light_states["internal_lamp"],
            "zone": ZONE_INTERIOR,
            "is_spot": False,
            "direction": (0.0, -1.0, 0.0),
            "cutoff_cos": -1.0,
        },
        {
            "position": (0.0, 3.72, -0.3),
            "color": (0.18, 0.78, 1.00),
            "intensity": 3.00,
            "enabled": light_states["internal_disco"],
            "zone": ZONE_INTERIOR,
            "is_spot": False,
            "direction": (0.0, -1.0, 0.0),
            "cutoff_cos": -1.0,
        },
    ]


def upload_lights():
    lights = current_lights()
    for i, light in enumerate(lights):
        glUniform3f(loc_light_pos[i], *light["position"])
        glUniform3f(loc_light_color[i], *light["color"])
        glUniform1f(loc_light_intensity[i], light["intensity"])
        glUniform1i(loc_light_enabled[i], GL_TRUE if light["enabled"] else GL_FALSE)
        glUniform1i(loc_light_zone[i], light["zone"])
        glUniform1i(loc_light_is_spot[i], GL_TRUE if light["is_spot"] else GL_FALSE)
        glUniform3f(loc_light_direction[i], *light["direction"])
        glUniform1f(loc_light_cutoff_cos[i], light["cutoff_cos"])


def draw_gpu_mesh(gpu_mesh):
    glBindVertexArray(gpu_mesh.vao)
    for segment in gpu_mesh.segments:
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, segment["texture_id"])
        glDrawArrays(GL_TRIANGLES, segment["start"], segment["count"])
    glBindVertexArray(0)


def draw_node(scene_node):
    model = build_model_matrix(scene_node)
    send_matrix(loc_model, model)
    send_normal_matrix(model)
    glUniform1i(loc_unlit, GL_FALSE)
    set_material(scene_node["material"], scene_node["zone"])
    draw_gpu_mesh(gpu_meshes[scene_node["mesh"]])


def draw_scene_nodes(wireframe=False):
    if wireframe:
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
    else:
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

    for item in scene_nodes:
        draw_node(item)

    glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
'''


markdown_controls = """
## 5. Controles e execucao

Os controles principais ficaram assim:

- `W`, `A`, `S`, `D`, `Espaco`, `C`, mouse: navegacao da camera;
- `T` / `G`: translacao do carro externo, levando junto a luz externa;
- `0`: liga/desliga a luz ambiente;
- `1`: liga/desliga a luz externa do carro;
- `2`: liga/desliga a luz interna da luminaria;
- `3`: liga/desliga a luz interna da bola de discoteca;
- `U` / `J`: aumenta/diminui a componente ambiente;
- `I` / `K`: aumenta/diminui a reflexao difusa global;
- `O` / `L`: aumenta/diminui a reflexao especular global;
- `P`: alterna malha poligonal;
- `Esc`: fecha a janela.

Com isso, a cena permite verificar visualmente todos os requisitos do Projeto 3.
"""


code_loop = r'''
last_frame = glfw.get_time()
print_lighting_status()

while not glfw.window_should_close(window):
    current_frame = glfw.get_time()
    delta_time = current_frame - last_frame
    last_frame = current_frame

    glfw.poll_events()
    process_input(delta_time)

    glClearColor(0.015, 0.015, 0.022, 1.0)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    shader.use()
    send_matrix(loc_view, view_matrix())
    send_matrix(loc_projection, projection_matrix())
    glUniform3f(loc_view_pos, camera_pos.x, camera_pos.y, camera_pos.z)
    glUniform1i(loc_ambient_enabled, GL_TRUE if ambient_enabled else GL_FALSE)
    glUniform1f(loc_ambient_level, ambient_level)
    glUniform1f(loc_global_diffuse, global_diffuse_level)
    glUniform1f(loc_global_specular, global_specular_level)
    upload_lights()

    glDepthMask(GL_FALSE)
    glUniform1i(loc_object_zone, ZONE_SHARED)
    glUniform1i(loc_unlit, GL_TRUE)
    glUniform3f(loc_base_color, 1.0, 1.0, 1.0)
    glUniform3f(loc_emissive_color, 0.0, 0.0, 0.0)
    glUniform1f(loc_emissive_strength, 0.0)
    glUniform1f(loc_material_ambient, 1.0)
    glUniform1f(loc_material_diffuse, 0.0)
    glUniform1f(loc_material_specular, 0.0)
    glUniform1f(loc_material_shininess, 1.0)
    sky_model = glm.translate(glm.mat4(1.0), camera_pos)
    sky_model = glm.scale(sky_model, glm.vec3(60.0, 60.0, 60.0))
    send_matrix(loc_model, sky_model)
    send_normal_matrix(sky_model)
    draw_gpu_mesh(gpu_meshes["night_skybox"])
    glUniform1i(loc_unlit, GL_FALSE)
    glDepthMask(GL_TRUE)

    draw_scene_nodes(wireframe=False)
    if show_wireframe:
        draw_scene_nodes(wireframe=True)

    glfw.swap_buffers(window)

glfw.terminate()
print("Janela encerrada.")
'''


notebook = {
    "cells": [
        {"cell_type": "markdown", "metadata": {}, "source": lines(markdown_intro)},
        {"cell_type": "markdown", "metadata": {}, "source": lines(markdown_paths)},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": lines(code_main)},
        {"cell_type": "markdown", "metadata": {}, "source": lines(markdown_shader)},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": lines(code_shader)},
        {"cell_type": "markdown", "metadata": {}, "source": lines(markdown_loader)},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": lines(code_loader)},
        {"cell_type": "markdown", "metadata": {}, "source": lines(markdown_scene)},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": lines(code_scene)},
        {"cell_type": "markdown", "metadata": {}, "source": lines(markdown_controls)},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": lines(code_loop)},
    ],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "name": "python",
            "version": "3.12",
        },
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}


NOTEBOOK_PATH.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(f"Notebook atualizado em: {NOTEBOOK_PATH}")
