# Optional Video and Narration Mode

## Explain through motion

Start from what the audience wants to understand. Phenomenon-first explanation works when useful; familiar formulas or concept distinctions can also provide a hook. Supply necessary background for technical terms without replacing mechanisms with misleading analogies.

Drive instruments, arrows, numerical labels, and highlighted formula terms from the same physical state. Make corresponding changes visibly linked. Render formulas properly; preserve relevant preceding steps instead of abruptly replacing entire pages. Follow a persistent object through transitions. Allow thinking time but remove empty gaps. Compose portrait and landscape covers separately; keep clear balanced titles and avoid overlap/stretching. Use direct, concrete language rather than inflated claims.

## Deploy narration deliberately

Distinguish the agent's orchestration from an external TTS model. Preserve the project's approved voice unless asked to change it. Qwen3-TTS Voice Design, CustomVoice, and Base/Voice Clone serve different purposes. Consult the current [official Qwen3-TTS project](https://github.com/QwenLM/Qwen3-TTS), model card and license, then pin exact model ID/revision and compatible Python/PyTorch/CUDA/dependencies. Do not present old unverified commands as a working one-click deployment.

1. Inspect existing audio and jobs. Determine whether only selected segments need regeneration.
2. In an authorized private notebook, select an available GPU and inspect per-card VRAM, disk, and package compatibility. Test a representative sentence before batching.
3. Install official dependencies and obtain the selected model. Record source and versions; keep caches and private voice samples outside a reusable skill.
4. Clone only a voice the user has the right to use, with the required reference audio and accurate transcript. For voice design, use the requested description. Do not forward voice samples to another service without applicable authorization.
5. Segment by meaning. Test letters, Greek names, ambiguous words, numbers, and units. Listen when supported; otherwise explicitly identify ASR/waveform-only checks.
6. Split independent inputs across cards only after fit/concurrency validation. Save stable segment IDs, input/text hashes, generation configuration, native WAVs, and logs. Regenerate only changed segments.
7. Preserve native audio; save pause/gain/assembly edits separately. Use measured duration for short captions and animation cues. Avoid cuts inside words and late long captions.
8. Retrieve and verify outputs, then release your idle runtime. Temporary notebooks are not permanent storage.

In a deployment tutorial, simulated operations must be identified as illustrations. Show only verified commands, hardware, and outcomes; do not fabricate successful logs or results.
