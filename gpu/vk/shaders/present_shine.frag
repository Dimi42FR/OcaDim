#version 450
// (OcaDim 0.0.6) « Rue mouillee », en COUCHE TRANSLUCIDE a la presentation.
//
// Pourquoi une couche : mon tirage qui echantillonnait l'image de la frame generation pour la reecrire la corrompait (meme
// en recopiant sans calcul). Ici la couche ne lit RIEN : elle se melange a l'image deja affichee, comme les overlays
// d'ImGui, donc rien ne peut etre corrompu.
//
// Une chaussee mouillee = plus sombre, une lueur de ciel rasante, et quelques scintillements. Tout vient de la position a
// l'ecran (la rue est en bas), aucune profondeur, aucune normale.
layout(push_constant) uniform P {
    float strength;   // (0 = rien, 1 = plein)
    float time;       // (secondes)
    float pad0;
    float pad1;
} pc;

layout(location = 0) in vec2 v_uv;
layout(location = 0) out vec4 out_col;

float hash21(vec2 p) {
    p = fract(p * vec2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
}

void main() {
    const float y = v_uv.y;   // (0 en haut de l'ecran)
    // (la rue : le bas ; le plus mouille la ou elle s'eloigne, le premier plan plus mat)
    const float road = smoothstep(0.38, 0.62, y) * mix(1.0, 0.55, smoothstep(0.82, 1.0, y));
    const float band = smoothstep(0.42, 0.60, y) * (1.0 - smoothstep(0.60, 0.84, y));
    const float s = pc.strength * road;

    // (1) et (2) : la teinte froide de la pierre humide, plus dense vers l'horizon de la rue
    vec3 col = vec3(0.42, 0.46, 0.54);
    float a = clamp(0.16 * s * (0.45 + 0.55 * band), 0.0, 0.5);

    // (3) les scintillements : de petits points blancs, rares, uniquement sur la rue
    const vec2 gp = gl_FragCoord.xy / 2.5;
    float spark = 0.0;
    for (int k = 0; k < 3; k++) {
        const float ph = hash21(floor(gp) + float(k) * 17.0);
        const float life = fract(pc.time * (0.35 + 0.55 * ph) + ph);
        const float on = smoothstep(0.84, 0.89, life) * (1.0 - smoothstep(0.93, 0.99, life));
        const float spot = step(0.960, hash21(floor(gp) + 3.7 + float(k) * 5.1));
        spark += on * spot;
    }
    spark = clamp(spark, 0.0, 1.0) * s;
    col = mix(col, vec3(1.0, 0.98, 0.92), spark);
    a = mix(a, 0.45, spark);

    out_col = vec4(col, a);
}
