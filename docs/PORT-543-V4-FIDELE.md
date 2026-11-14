LE PORT FIDÈLE #543 (v4) — leur mécanique, nos structures
===========================================================
(Référence: D:\Emulateur\NX2navi-src runtime/vk_usnap.c + vk_backend.c
 replay_gate, branch pr543 @ 0407632, MIT)

== POURQUOI MES PORTS PAGE-LEVEL ONT ÉCHOUÉ (la leçon) ==
Leurs snapshots = LES BLOCS UNIFORMS LIÉS par la submission (les handles ->
les ranges exacts), copiés dans une arène PAR SOUMISSION (Taken), consommés
EN ORDRE par adopt. Mes ports: des pages 4K entières via la table d'entrées
GLOBALE (la dernière capture gagne pour tous) — la granularité et la
consommation ne correspondent pas à la sémantique par soumission.
Les flashs = les DONNÉES UNIFORMS (le soleil/les couleurs = les constantes
par frame dans les blocs UB) — leur fix snapshot exactement ça.

== LEUR MÉCANIQUE (vk_usnap.c, exacte) ==
1. Au submit (la submission attend): vk_usnap_take_later(handles) ->
   Taken{h: les handles, open: 1} empilé (la copie PAS encore prise).
2. Au signal (le thread signaleur): vk_usnap_take_open() -> taken_fill(t,
   t->h, t->n, 1) pour chaque open: LES RANGES COPIÉS maintenant (l'arène),
   depuis la mémoire vive à cet instant.
3. Au replay (en ordre): adopt(handles, n) -> consomme le Taken de la
   submission (les entrées d'avant, jamais arrivées au replay, libérées);
   si encore open (le replay est passé sans le signal): taken_fill(..., 0)
   — la copie au moment du replay, comme avant.
4. Les lectures de la submission: l'arène adoptée (les bytes au signal ✓).

== LE PORT DANS NOS STRUCTURES (v4) ==
La granularité: les RANGES UB que la partie reprise liera — connus par un
dry pass du reste (la machinerie existe: rmode=Dry collecte l'état aux
points — les ranges UB liés sont dans l'état des bindings aux par points).

1. AU STOP GATED (le replay thread, sous replay_mu, à la suspension):
   le dry pass du RESTE (from q.p) -> les ranges UB liés par la partie
   reprise: la liste {addr, n} (résolus depuis l'état aux points, comme
   ub_overlay les reçoit au record) -> tenue dans QueueRun (q.gate_ranges).
   Coût: un walk du reste, une fois par stop gated.

2. AU SIGNAL (event_signal_queued, le thread signaleur, la fenêtre):
   pour chaque QueueRun stopped dont l'event attendu == gpu (le registre
   gate_wait_gpu, v2 ✓): COPIER les ranges tenus depuis la MÉMOIRE VIVE
   (hos read direct, le thread signaleur, la fenêtre ✓) dans des buffers
   tenus (q.gate_copies: {addr, n, bytes}).

3. À LA REPRISE GATED (resume_queue): les ub_overlay/descriptor builds de
   la partie reprise: pour un range tenu: la base de l'overlay = la COPIE
   tenue (au lieu de memory_read_as_submitted) + les ub_updates du stream
   par-dessus (la structure d'ub_overlay inchangée: la base change seule).
   Les ranges non tenus: le chemin actuel. Les copies tenues libérées à la
   fin de la submission.

4. L'INTERRUPTEUR: RX_VK_EVENT_GATE=1 (off par défaut). Le late_fix et le
   resume_capture COEXISTENT (la leçon v1: ne rien retirer).

== LES PIÈCES DE CODE ==
- Le dry pass du reste à la suspension: replay(none, state, from=q.p) en
  rmode=Dry — la machinerie existe (run_submit's parallel path l'utilise);
  la collecte des ranges UB: les bindings de l'état aux par points —
  NOUVEAU: collecter les {addr, n} des ub bindings (l'état: les bindings
  UB courants de la soumission — la structure où ils vivent: NvnState's
  ub bindings / les descripteurs' ranges — À LOCALISER dans le dry pass).
- La copie au signal: host->gpu_read (le vkgpu->guest mapping ✓) ou le
  guest_base direct — le thread signaleur lit la mémoire vive ✓.
- L'intégration overlay: ub_overlay(addr, n, base, alloc) — base = la
  copie tenue si (addr, n) est tenu (le lookup: q.gate_copies par addr/n);
  memory_read_as_submitted remplacé par memcpy de la copie pour la part
  hors ub_updates ✓ (la boucle ub_updates par-dessus inchangée ✓).

== CONFIRMATION DE FAISABILITÉ (2026-11-14, le code relu) ==
LA SOURCE DES RANGES TROUVÉE: vk_draw.cpp:3315 — l'overlay UBO lit
  s.ubo[stage][index-3] (nvn_p_bind_buf: u.addr, u.size) — LES RANGES LIÉS
  SONT DANS L'ÉTAT NVNSTATE ✓. Et les ParPoint du dry pass portent des
  copies de l'état (ParPoint{s, ...} vk_replay.cpp:1737) ✓ -> la collecte
  des ranges à la suspension = parcourir les par points du dry pass du
  reste et tirer s.ubo[*][*].addr != 0 ✓ FAISABILITÉ VERROUILLÉE.
L'IMPLÉMENTATION PRÉCISE (la prochaine session, ~2-3 h):
  1. À la suspension gated (run_submit's stop, sous replay_mu): le dry
     pass du reste (from = le point d'arrêt, l'état = cur_state ✓) ->
     les ranges: pour chaque ParPoint: s.ubo[st][i].addr != 0 ->
     {addr, min(size, maxUniformBufferRange)} -> dédup/merge -> q.gate_ranges
     (un global sous mutex: le signal path ne peut pas toucher qruns).
  2. Au signal (event_signal_queued, le ring match ✓): pour chaque range
     tenu: la copie (host->guest_base + addr, n octets) -> gate_held_copies
     (le global sous le même mutex).
  3. Dans ub_overlay (vk_replay.cpp:1083): AVANT memory_read_as_submitted:
     le lookup (addr, n) dans gate_held_copies (la couverture: n_held >= n) ->
     la base = memcpy des bytes tenus (au lieu de la capture) -> la boucle
     ub_updates inchangée par-dessus ✓.
  4. Le cycle de vie: gate_held_copies consommé à la fin de la reprise
     gated (les ranges non couverts: le chemin actuel ✓).
  5. Le coût: le dry pass du reste par stop gated (2-5 ms?) — seulement
     sous la gate (off par défaut) et pour les stops gated.


== L'ORDRE DES TESTS ==
1. La gate v4 au stop (les ranges collectés) + au signal (les copies) +
   à la reprise (les overlays tenus) — async + parallel 4/32 + late_fix.
2. Le verdict: les flashs (les yeux + le flash detector) + les fps.
3. Si tient: la PR upstream (le port fidèle documenté, les deux références).
