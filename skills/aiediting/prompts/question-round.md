# How a question round is written

For the agent running the interview (`phases/interview.md`), and for a subagent asked to draft a round.

**In the person's language** (Russian unless they write in another one), plain words, no step ids and no
profile keys. One theme per round, 3–4 questions, numbered. Each question:

1. the question in one line;
2. **the recommended variant and why** in half a line — what most people of this format choose and
   what it costs them;
3. where the answer changes what the video looks like — **the example on their source**: «на кадре 2
   вашего урока», a trial piece on the dashboard, variants side by side;
4. ⚑ before a question with no safe default — there the person picks a letter themselves.

```
Тема 2 из 6 — паузы и оговорки · урок

1. Паузы дольше 0,5 с вырезаем, оставляя 0,12 с вокруг речи. Я бы так и оставил — темп живой,
   слова не обрезаются. Пример — проба 01 на дашборде (минута с 03:10 вашей записи).
2. «Э-э», «м-м» вырезаем, «ну», «вот» оставляем. Я бы так: без «ну» речь звучит рублено.
3. ⚑ Повторы фразы:
   а) оставлять последний удачный дубль — список покажу на согласование;
   б) не трогать.
   Тут выберите сами — от этого зависит длина ролика.

Ответьте, например: «3а, остальное ок» — или «ок», если со всем согласны (кроме ⚑).
```

- Never ask for a key, a password or a token; ask *which* service, and name the variable the person
  fills in themselves.
- Never invent a fact about them (their folder, their brand names, their music) as a recommendation:
  «не знаю» stays a visible gap in the profile.
- An answer that opens a new question → it goes into the next round of the same theme.
