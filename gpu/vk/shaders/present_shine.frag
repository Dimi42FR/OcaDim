#version 450
// (OcaDim 0.0.6) Les EFFETS, en une couche translucide posee a la presentation.
//
// Aucune lecture d'image, aucune animation : elle se melange a l'image deja affichee, comme les overlays d'ImGui. Rien ne
// peut etre corrompu ni clignoter.
//
//   brillance : la rue parait humide (teinte froide, plus dense vers l'horizon de la rue)
//   vignette  : les bords s'assombrissent
//   teinte    : chaud (orange) ou froid (bleu) sur toute l'image
//   grain     : une texture de pellicule, fixe (aucune animation)
layout(push_constant) uniform P {
    float sheen;      // (0..1 : la brillance de la rue)
    float vignette;   // (0..1)
    float warm;       // (-1..1 : negatif froid, positif chaud, 0 neutre)
    float grain;      // (0..1)
} pc;

layout(location = 0) in vec2 v_uv;
layout(location = 0) out vec4 out_col;

float hash21(vec2 p) {
    p = fract(p * vec2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
}

void main() {
    const vec2 uv = v_uv;
    vec3 col = vec3(0.0);   // (la couleur de la couche)
    float a = 0.0;          // (sa transparence cumulee)

    // (1) la brillance : le bas de l'image est la rue ; plus dense vers l'horizon de la rue)
    {
        const float y = uv.y;
        const float road = smoothstep(0.36, 0.62, y);
        const float band = smoothstep(0.40, 0.58, y) * (1.0 - smoothstep(0.58, 0.82, y));
        const float wa = clamp(0.26 * pc.sheen * road * (0.55 + 0.45 * band), 0.0, 0.45);
        const vec3 wet = vec3(0.33, 0.37, 0.46);
        col = wet * wa + col * (1.0 - wa);
        a = wa + a * (1.0 - wa);
    }

    // (2) la vignette : un assombrissement qui augmente vers les bords)
    {
        const vec2 d = uv - vec2(0.5);
        const float r = length(d * vec2(1.12, 1.0)) * 1.4142;
        const float v = clamp(pc.vignette * smoothstep(0.52, 1.05, r), 0.0, 0.85);
        col = col * (1.0 - v);   // (une vignette assombrit, elle n'ajoute pas de couleur)
        a = v + a * (1.0 - v);
    }

    // (3) la teinte : chaud (orange) ou froid (bleu), en transparence legere)
    if (pc.warm != 0.0) {
        const vec3 w = pc.warm > 0.0 ? vec3(1.0, 0.62, 0.32) : vec3(0.38, 0.58, 1.0);
        const float t = 0.16 * abs(pc.warm);
        col = w * t + col * (1.0 - t);
        a = t + a * (1.0 - t);
    }

    // (4) le grain : une valeur fixe par pixel (aucune animation), posee tres legerement)
    if (pc.grain > 0.0) {
        const float g = hash21(floor(uv * vec2(1920.0, 1080.0)));
        const float t = 0.12 * pc.grain * g;
        col = vec3(g) * t + col * (1.0 - t);
        a = t + a * (1.0 - t);
    }

    out_col = vec4(col, clamp(a, 0.0, 0.9));
}
