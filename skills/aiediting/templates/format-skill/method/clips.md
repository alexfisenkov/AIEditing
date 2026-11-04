## Clips from a finished video

When the question is `clips`, the rubric's scores only find phrases that start well; they do not know what a phrase is
about. Read the whole text and pick by these, then write the answer yourself, as a list of your own:

- **It stands alone.** Someone who has seen nothing else understands it: one thought, with its start and its end.
- **It shows something.** An action on screen or a result beats talk about them.
- **It makes the viewer want the whole video,** and does not replace it.
- **It points at nothing the viewer does not have.** «Под этим видео», «ниже в описании», «как я уже говорил», «скоро
  научимся» are false in a short, where the only way on is the call to action. Such a sentence goes into `drop`.
- **It starts on the thought:** on «Саша, почему ты…», not on «Ну и на всякий случай уточню». It ends on a full stop.
- **Different clips, different thoughts,** taken through the whole video.

An item: `{"id": "c01", "name": "имя файла", "start": …, "end": …, "drop": [[a, b]], "said": "…"}`, and its id in `chosen`.
Times are those of a word's start and end in the words file. Read the sentence across every `drop`: it must stay correct.

`max_seconds` is the whole finished clip: its speech ÷ `speed`, plus `cta_tail` where the format ends on a call to action. So the
source may run longer by the rate of `speed`, and shorter by the tail.

