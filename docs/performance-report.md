# Report slow performance

If the game runs slowly, stutters or hitches, a normal bug report often isn't enough for the team to find out why. This
page shows how to have the game measure itself while it is slow. You only add a few lines to a text file: you don't need
to build anything again or install any tools.

## 1. Turn the measurements on

In the game folder (the folder with `image.bin` in it: `Games\Longshot` in your user folder on Windows, `~/Games/Longshot`
on Linux, unless you chose another one), create a text file named **`longshot_env.txt`** that contains these lines:

```
HOS_FPS_LOG=1
HOS_THREAD_TIMES=5
RX_VK_PASS_TIMING=1
RX_VK_SLOW_LOG=50
```

| Line | What it adds to the log |
|---|---|
| `HOS_FPS_LOG=1` | The frame rate cap, VRR and the game's speed |
| `HOS_THREAD_TIMES=5` | Every 5 seconds, which parts of the game keep the CPU busy |
| `RX_VK_PASS_TIMING=1` | How long the graphics card spends on each part of a frame |
| `RX_VK_SLOW_LOG=50` | Details for every frame that takes more than 50 ms: what each stutter was spent on |

Without any of these lines, the log already records the frame rate and the spread of frame times every 5 seconds.

On Windows, check that the file isn't really called `longshot_env.txt.txt`: in File Explorer, turn on **View → Show →
File name extensions**.

### If it stutters

If the problem is short freezes or hitches rather than a low frame rate all the time, add one more line:

```
HOS_RECORD_STUTTERS=1
```

Each time a frame takes 50 ms or longer, the game then writes down what every part of it was doing during that frame,
into the `logs` folder in the game folder: a file `slow_frame-1.txt` for the first stutter, `slow_frame-2.txt` for the
next, and so on (40 at most). It also writes `longshot_frames.csv` there, a line for every frame, so the team can see
how each stutter fits in with the frames around it. It makes the game a little slower while it is on.

## 2. Play where it's slow

1. Start the game. If it was already running, close it and start it again, because it only reads the file at startup.
2. Go to the place where it runs badly and stay there for **60 to 90 seconds**. Do the same thing the whole time, for
   example stand still, turn the camera or walk one route. Write down what you did.
3. While it's still slow, open the menu (<kbd>F1</kbd>), go to **Gameplay** and choose **Bug report**. This saves a
   folder in `bug-reports` in the game folder with the log, a screenshot and your PC's details, with your user name
   taken out.
4. Quit the game normally.

## 3. Send it

Send the team, on [Discord](https://discord.gg/magicbean) or with a [report](https://git.magicbean.dev/MagicBeanDev/Longshot/issues/new):

- the **bug report folder** from step 3, and `longshot_log.txt` from the game folder's `logs` folder;
- if you added `HOS_RECORD_STUTTERS=1`: the `slow_frame-*.txt` files and `longshot_frames.csv` from the same `logs`
  folder (zip them if there are many), and say about when in your play the worst stutters were;
- **where** you were in the game, and **what you did** there;
- your **settings**: the quality preset, render resolution, upscaler, frame generation and V-Sync (or a screenshot of
  the menu);
- your **graphics card and driver version**.

Send nothing else from the game folder: no game files, keys or saves. The files above hold only times, the names of the
game's threads and addresses in its code, nothing of yours.

## 4. Turn it off again

Delete `longshot_env.txt`, or the lines you added to it. Measuring costs a little speed, so don't leave it on while you
play normally. You can delete the `slow_frame-*.txt` files and `longshot_frames.csv` once they are sent; the next run
with the line writes them again.

If you already had a `longshot_env.txt` before step 1 (with a workaround from [common problems](common-issues.md), for
example), add the lines to it rather than replacing it, and remove only those lines afterwards.
