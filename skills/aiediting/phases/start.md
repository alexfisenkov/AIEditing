# Start

Read when `/aiediting` is called and `.aiediting-work/state.js` in the current folder is absent or
finished. An unfinished one → `phases/resume.md` instead. The person asked for no questions → §1 here,
then `phases/no-questions.md`. Said in the middle of a workshop → `phases/no-questions.md`, §1.

## 1. Find the skill and the tool

```bash
AE=$(find -L ~/.agents/skills ~/.claude/skills ~/.codex/skills ~/.cursor/skills ~/.gemini/skills \
        .agents/skills .claude/skills -maxdepth 4 -path '*/aiediting/tools/ae.py' 2>/dev/null | head -1)
echo "$AE"
```

`<skillDir>` is the folder two levels above `ae.py`. Keep the full path in mind for the whole session;
on Windows (Git Bash) pass it through `cygpath -m`. If Python 3.9+ is missing, install a supported
version through the system's normal package manager, then retry. If installation fails, name the
actual platform or permission error.

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

## 3. Get to know the person: one message

Before the first choice of a format, once per person and computer. Skip it, in whole or in part, for what is already
known: `ae.py library where` and `status` (a library may answer much of it), `ae.py list-skills` (formats they have), the
file `обо-мне/кто-я.md` of the library, the draft profiles. Never ask twice what an earlier run or a file already says. A call
that names a format and a source (`/aiediting refine монтаж-урок`) does not wait for this: ask it after the first trial, or not at all.

`ae.py ask question --note "знакомство"`, then **one message**, short and in a list; the person answers in any order and
may skip:

```
Чтобы собрать монтаж под вас, расскажу, что спрошу, а вы ответите одним сообщением, как получится:
1. Какой у вас компьютер (Mac или Windows), сколько свободного места на диске? Есть внешний диск?
2. Какие ролики делаете: YouTube, Reels и Shorts, уроки, эфиры, влоги? Что важнее всего сейчас?
3. На что снимаете: телефон или камера, сколько камер, лог-профиль? Чем пишете звук?
4. Есть ли программа для монтажа, и какая? Например, DaVinci. Если нет, это нормально.
5. Про что ваш блог и для кого ролики?
6. Сколько у вас своего материала: галерея телефона, футажи с камеры, архив Instagram?
7. Какие сервисы уже есть: чистка голоса (Auphonic), музыка (Epidemic Sound), другие?
8. Пришлите 1–3 ролика, которые нравятся по монтажу, и 1–2, которые не нравятся.
9. Чего нельзя показывать в роликах: людей, места, темы?
```

Do not add questions of your own and do not ask a key: «есть ли сервис» is a yes or a no. Where the answer is «нет» or «не
знаю», nothing is asked again, and nothing is set up for it.

**Where the answers go.** What changes a format goes into its draft later, by `phases/interview.md`
(`ae.py profile set`, `ae.py profile taste`). What is about the person goes into the library when one is connected
(`обо-мне/кто-я.md` for the blog, the audience and the equipment; «чего нельзя» through `ae.py library forbid "<кто или что>"`), in their own words and with
years, short. No library: it stays in the draft profile's taste lines, and nothing personal is written anywhere else.
A fact they did not give is never invented (rule 2).

**The personal plan.** After the answers, one short list in their language: what is already there, what to set up and in what
order, what can be skipped. A step goes into the plan only when their answers call for it. Ends with the first step and a
question, not with the whole road:

```
Что уже есть: ffmpeg, whisper, формат «урок».
Что поставить: ничего лишнего. DaVinci пока не нужен: правки скажете по таймкодам.
Что можно пропустить: чистка голоса и музыка, пока не захотите.
Начнём с пробного монтажа вашей записи. Ок?
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

«Да» → `ae.py library set <folder they choose>`; the pointer is one per computer and every format skill finds it; the description
of files is then begun after the first trial (`phases/interview.md`, the theme «Own footage and the library»). Nothing here
waits for it. «Нет» or silence → no library, no inserts, nothing broken.

`ae.py answered --note "<short>"`. Less is better: if they want more, they say so, or ask «может, ещё сделать побольше?».

## 4. The first question: create or refine

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

## 5. Check the environment

`python3 "<skillDir>/tools/ae.py" setup --check` verifies the full supported toolkit. If the person
already asked to install AIEditing, finish installation with `setup` before the workshop; copying the
skill with `npx skills add` did not install its dependencies. For a requested capability with a missing
dependency, use `setup --steps <steps> --asr <provider>` to repair that subset and verify again.
Announce total heavy downloads once. The request to install or use the capability is enough for its
local dependencies; no separate question per tool.
