# Start

Read when `/aiediting` is called and `.aiediting-work/state.js` in the current folder is absent or
finished. An unfinished one → `phases/resume.md` instead. The person asked for no questions → §1 here,
then `phases/no-questions.md`. Said in the middle of a workshop → `phases/no-questions.md`, §1.

## 1. Find the skill and the tool

`<skillDir>` is the folder of the `SKILL.md` you loaded, not of another copy. Most agents tell you where it is: Claude Code puts
it into `SKILL.md` («The tool»), OpenClaw too, Codex lists the path of `SKILL.md` with the skill, Gemini CLI names the folder when
the skill is activated. Only when you do not know it, look, the folders of this project first and then the global ones:

```bash
AE=$(find -L .agents/skills .claude/skills .gemini/skills skills \
        ~/.agents/skills ~/.claude/skills ~/.codex/skills ~/.cursor/skills ~/.gemini/skills ~/.openclaw/skills \
        -maxdepth 4 -path '*/aiediting/tools/ae.py' 2>/dev/null | head -1)
echo "$AE"
```

`<skillDir>` is then the folder two levels above `ae.py`. Its `SKILL.md` must carry the same `metadata.version` as the one you
read: two copies of different versions lie on this computer otherwise, so take the one that matches and say so in one line.
Keep the full path in mind for the whole session; on Windows (Git Bash) pass it through `cygpath -m`. If Python 3.9+ is missing,
install a supported version through the system's normal package manager, then retry. If installation fails, name the actual
platform or permission error.

## 2. Open the workshop

```bash
python "<skillDir>/tools/ae.py" init --mode new --title "<what the person asked, in their words>"
```

It creates `.aiediting-work/` in the current folder, copies the dashboard, raises a server on
127.0.0.1 and prints the address. Renders are large and a synced folder (iCloud, Dropbox) slows them down
and copies them everywhere; there, set `AIEDITING_WORK=<folder outside it>` on this and every later `ae.py`
call, because a shell may go back to its first folder between calls. Check where it printed. Open it **once,
yourself**, before the first question:

- Claude Code: `preview_start({url: "http://localhost:PORT"})`, then navigate to `/dashboard.html`.
- No pane: `open` / `start` / `xdg-open` on `.aiediting-work/dashboard.html`.
- Say the address in the chat too. Over SSH or in CI no server is raised — give the file path.
- «Дашборд пропал» → a bare `python "<skillDir>/tools/ae.py"` raises it again on the same port.

A line `Новая версия: …` in what `init` printed: say it to the person in one phrase, now, as it is (which version came out, which
one they have, how to update this copy). Update only on their word, and never in the middle of a session: «Updating AIEditing» in
`SKILL.md`.

## 3. Check the environment

`python3 "<skillDir>/tools/ae.py" setup --check` verifies the full supported toolkit, before the plan: the plan says what is
already there by this check, not by a guess. If the person already asked to install AIEditing, finish installation with `setup`
here; copying the skill with `npx skills add` did not install its dependencies. For a requested capability with a missing
dependency, use `setup --steps <steps> --asr <provider>` to repair that subset and verify again. Announce total heavy downloads
once. The request to install or use the capability is enough for its local dependencies; no separate question per tool. Nothing
else is installed now: what a format needs is repaired when that format is chosen (`phases/build.md`, §2).

## 4. Get to know the person: one message

Before the first choice of a format, once per person and computer. Skip it, in whole or in part, for what is already
known: `ae.py intro` (what they told an earlier run in this folder), `ae.py library where` and `status` (a library may answer much
of it), `ae.py list-skills` (formats they have), the file `обо-мне/кто-я.md` of the library, the draft profiles. Never ask twice
what an earlier run or a file already says. A call that names a format and a source (`/aiediting refine монтаж-урок`) does not
wait for this: it is asked once after the «да» to the first trial (`phases/trial.md`), or not at all.

`ae.py ask question --note "знакомство"`, then **one message**, short and in a list; the person answers in any order and
may skip:

```
Чтобы собрать монтаж под вас, расскажу, что спрошу, а вы ответите одним сообщением, как получится:
1. Какой у вас компьютер (Mac или Windows), сколько свободного места на диске? Есть внешний диск?
2. Какие ролики делаете: YouTube, Reels и Shorts, уроки, эфиры, влоги? Что важнее всего сейчас?
3. На что снимаете: телефон или камера, сколько камер? Если камера снимает бледную серую картинку (режим LOG), скажите. Чем пишете звук?
4. Есть ли программа для монтажа, и какая? Например, DaVinci. Если нет, это нормально.
5. Про что ваш блог и для кого ролики?
6. Сколько у вас своего материала: галерея телефона, футажи с камеры, архив Instagram?
7. Какие сервисы уже есть: чистка голоса (Auphonic), музыка (Epidemic Sound), другие?
8. Пришлите 1–3 ролика, которые нравятся по монтажу, и 1–2, которые не нравятся.
9. Чего нельзя показывать в роликах: людей, места, темы?
```

Do not add questions of your own and do not ask a key: «есть ли сервис» is a yes or a no. Where the answer is «нет» or «не
знаю», nothing is asked again, and nothing is set up for it.

**Where the answers go.** At once, in their own words, short: `ae.py intro set <key>="<answer>" …`, one key per point:
`computer`, `videos`, `camera`, `program`, `blog`, `materials`, `services`, `liked`, `disliked` (the two halves of 8), `forbid`
(several through «;»). They are kept in the state of the workshop folder and nowhere else, and they survive a fresh start in that
folder. From here on **every phase reads them with `ae.py intro` instead of asking**:

| Answer | Taken by | Instead of |
|---|---|---|
| `videos` | `phases/formats.md`: the formats are proposed from it, to confirm | the open question of formats |
| `blog` | the draft: `ae.py formats` writes it as a taste line by itself | the theme «Niche and audience» |
| `camera` | `phases/interview.md`: «Cameras» only with more than one camera or a sound recorded apart; LOG footage is a note for the colour | the theme «Cameras» |
| `program` | `phases/interview.md`: «Timeline» knows the program; DaVinci is offered there once, never here | the question of the program |
| `services` | `phases/interview.md`: «Voice», «Music» only for a service they have or want | asking about each service |
| `materials` | the library question below | |
| `liked`, `disliked` | taste lines of the draft by themselves; `phases/design.md` and `phases/trial.md` look at them | asking what style they like |
| `forbid` | a taste line, and with a library its list `чего-нельзя.md` | |
| `computer` | the plan: room on the disk for heavy downloads | |

What is about the person goes into the library when one is connected: `ae.py intro apply` puts the blog and the audience into
`обо-мне/блог.md`, the videos and the equipment into `обо-мне/кто-я.md`, and what must never be shown into `чего-нельзя.md`, with
the date, once. No library: nothing personal is written outside the workshop folder and the drafts. A fact they did not give is
never invented (rule 2).

**The personal plan.** After the answers, one short list in their language: what is already there (by §3 and `list-skills`),
what to set up and in what order, what can be skipped. A step goes into the plan only when their answers call for it. Its first
step is always the choice of §5, and it ends with a question, not with the whole road:

```
Что уже есть: ffmpeg и whisper стоят, скиллов монтажа пока нет.
Что поставить потом: Remotion (≈700 МБ), если выберете графику поверх видео.
Что можно пропустить: чистку голоса и музыку, пока не захотите.
Первый шаг: решить, делаем новый скилл монтажа или дорабатываем ваш. Начнём?
```

**Their own materials and the library.** The one question to explain in full, slowly and with no pressure, because a person
can be frightened by «опись галереи». Ask it once, after the plan, and take «нет» as a full answer:

```
Ещё одно, и это по желанию. Можно использовать ролики и фото, которые вы уже снимали: когда вы говорите «я катался на
мотоцикле», в монтаж встанет настоящий кадр оттуда, а не картинка из интернета. Для этого нужна библиотека: обычная папка на
вашем диске, куда я положу список ваших файлов с короткими описаниями. Файлы никуда не копируются и не уходят в интернет,
описания остаются у вас на компьютере. Описывать архив можно постепенно, по кусочку, и первый ролик не ждёт: сначала
смонтируем его без библиотеки. Подключить библиотеку? Если нет, всё работает как обычно, вернуться к этому можно в любой день.
```

«Да» → `ae.py library set <folder they choose>`, then `ae.py intro apply`; the pointer is one per computer and every format skill
finds it. The description of their files begins after the «да» to the first trial (`phases/trial.md`); nothing here waits for it.
«Нет» or silence → no library, no inserts and no stock, nothing broken.

`ae.py answered --note "<short>"`. Less is better: if they want more, they say so, or ask «может, ещё сделать побольше?».

## 5. The first question: create or refine

`python "<skillDir>/tools/ae.py" list-skills` lists the `монтаж-*` skills on this computer: the ones AIEditing has built, and
the ones written by hand or by someone else, marked so. Any of them can be refined.
Then `ae.py ask choice --note "новый скилл или доработка"` and one message:

```
Что делаем?
1. Новый скилл монтажа — под формат, который выберете.
2. Доработать существующий: монтаж-урок, монтаж-эфир.   ← only the names list-skills printed
```

No skills yet → say so and go straight to a new one. The call already named it («/aiediting refine
монтаж-урок», «доработай урок») → do not ask again.

A call that names a format with paths («/aiediting нарезка») has named the format, not the path: the path is still offered and
probed (`phases/formats.md`, «A format with paths»). A call that comes with a finished video goes to the same format, and the
first thing to find out about it is where it came from (`phases/sources.md`, «A finished video»).

- **New** → `ae.py stage formats`, read `phases/formats.md`.
- **Refine** → `ae.py init --mode refine --fresh --title "Доработка <name>"`, read `phases/refine.md`.
