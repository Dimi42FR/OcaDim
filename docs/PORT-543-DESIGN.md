PORT #543 (NX2navi) -> LONGSHOT - DESIGN CORRIGE (apres analyse complete)
=========================================================================
Branche de reference: D:\Emulateur\NX2navi-src (pr543 @ 0407632, MIT)
Cible: gpu/vk/vk_replay.cpp (async: submit_q 5325-5331, run_submit 2503-2563,
replay_handle NOP_WAIT_EVENT 1229-1248, ev_cpu_apply)

== POURQUOI L'ASYNC CASSE CHEZ NOUS (le mecanisme exact) ==
1. OoT empile les submissions des queues de travail, qui attendent un event
   que la queue principale signale; le CPU signale apres avoir ecrit les
   donnees de la frame.
2. Sous RX_VK_ASYNC=1, la capture est prise AU SUBMIT (submit_q:5326) - les
   donnees de la frame ne sont pas encore toutes ecrites -> capture en retard
   sur la frame.
3. Le resume d'une submission stoppee (schedule -> run_submit) prend SA
   capture au resume - APRES le signal, mais la fenetre de course est la:
   entre "frame k ecrite" (le signal) et "la reecriture de la frame k+1 qui
   commence tout de suite apres", le jeu recrit le double-buffer que la
   submission k lit encore. La capture du resume peuttenir k+1 -> frames
   blanches/noires (28/1000).
   => CORRECTION possible des deux cotes: capture AU SIGNAL (ni au submit,
   ni au resume).

== LEUR MACHINE A ETATS (vk_backend.c:389-479), traduite ==
Etats (atomiques):
- g_waiting: le replay est dans la gate
- g_blockers: threads du jeu qui attendent le replay (fence pas encore
  soumise, drain, queue pleine, frame bound) -> sortie de gate FORCE: le jeu
  ne peut pas signaler avant que cette attente se termine
- g_taking: le thread qui signale est en train de prendre les copies tenues
  (entre le signal et la fin des copies)
- g_stuck: un timeout de gate a expiré; on ne gate plus jusqu'au prochain
  signal (evite d'empiler les retards)
Constantes: GATE_NS = 50 ms; le signal = l'event CPU de la frame.

Points d'accroche chez eux:
- submit call: gate_later(h,n) -> la copie uniform est prise AU SIGNAL
  (vk_usnap_take_later), pas au submit
- replay thread: replay_gate(h,n) AVANT d'enregistrer une submission qui
  attend: boucle sur (blockers>0 -> escape | !cpu_pending && !taking -> go |
  GATE_NS -> stuck); le signalement traite les copies tenues (g_taking)
- le signal: gfx_event_signalling prend les copies tenues LA, tout de suite
- les waits: be_fence_wait compte les blockers (un fence dont la valeur n'a
  pas ete remise par le replay = une attente du replay)

== CE QUE LONGSHOT A DEJA ==
- suspend aux waits: replay_handle -> NOP_WAIT_EVENT -> suspend_at
  (submit_job les re-programme: sync_watch/schedule)
- blocked_n + update_blocked(): les threads du jeu qui attendent du travail
  stoppe = NOTRE compteur de blockers, deja existe
- JOB_EVENT_SIGNAL: le signal CPU arrive a la queue (ev_gpu/ev_value,
  Job:5106) - le point ou brancher la capture tenue
- submit_order_mu: captures et submits deja ordonnes
- ev_cpu_apply: l'application des signaux CPU aux valeurs d'events

== IMPLEMENTATION (quand on l'attaque) ==
1. Job.defer_capture (bool) pose dans submit_q async si le stream contient
   un NOP_WAIT_EVENT (pre-walk avec le walk existant, op headers: stream_work)
2. submit_q async: si defer_capture -> PAS de memory_capture_submit au submit
3. Le signal CPU (la ou JOB_EVENT_SIGNAL est enquee, cote host): si des
   submissions defer_capture attendent -> memory_capture_submit() ICI, sur le
   thread du jeu (le point g_taking), et marquer la capture comme celle des
   resumes de ces submissions (attacher au value: la memoire des resumes doit
   lire CELLE-la, pas en reprendre une au resume)
4. run_submit au resume d'une submission defer_capture: gate (blockers>0 ->
   escape | signal traite -> go | 50 ms -> stuck), puis proceed; sa memoire
   utilise la capture prise au signal
5. Interrupteurs: RX_VK_EVENT_GATE (defaut 1 quand RX_VK_ASYNC=1),
   RX_VK_EVENT_ORDER_ASYNC (l'ordre des events sur le thread de replay -
   chez nous submit_job le fait deja par queue: verifier le cas de la queue
   principale vs queues de travail)
6. Validation: le flash detector du projet (scripts/run-vk.ps1) sur la meme
   route Kokiri que NX2navi a utilisee: 0 frame noire attendu, fps ~ synchrone
NOTES:
- le pas 3 est le delicat: attacher une capture a des resumes - voir comment
  submit_memory_work/memory_sync choisissent leurs captures (vk_memory.cpp
  cur_cap_gen/cap_entry) pour eviter de casser la regle 2 (rien n'est lu de
  la memoire vive)
- g_stuck: apres un timeout, ne plus gater jusqu'au prochain signal (leur
  lecon: sinon les retards s'empilent)
