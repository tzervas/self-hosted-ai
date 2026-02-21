# Music Production Suite - Professional Audio Capabilities

**Goal**: Enable professional-grade music production entirely self-hosted

---

## 🎼 Music Production Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│ Open WebUI (Natural Language Interface)                    │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┴──────────────┬──────────────────────┐
        ↓                              ↓                      ↓
┌───────────────────┐     ┌────────────────────┐   ┌─────────────────┐
│ Music Tools       │     │ Production Tools   │   │ Mastering Tools │
│ - Generation      │     │ - Mixing           │   │ - Finalizing    │
│ - Composition     │     │ - Effects          │   │ - Export        │
│ - Arrangement     │     │ - Automation       │   │ - Formats       │
└─────────┬─────────┘     └──────────┬─────────┘   └────────┬────────┘
          │                          │                       │
          └──────────────┬───────────┴───────────────────────┘
                         ↓
            ┌────────────────────────────┐
            │ Audio Processing Engine    │
            │ - MusicGen (generation)    │
            │ - AudioLDM2 (SFX/stems)    │
            │ - RVC (voice conversion)   │
            │ - Demucs (stem separation) │
            │ - FFmpeg (processing)      │
            └────────────────────────────┘
```

---

## 🎹 Music Production Tools (20+ Tools)

### Category 1: Music Generation (Deep Controls)

1. **`music_generator_pro.py`** ⭐ *NEW*
   - **Genre-specific generation** (20+ genres)
   - **Deep controls**:
     - Tempo (BPM: 60-200)
     - Key/Scale (C major, A minor, etc.)
     - Time signature (4/4, 3/4, 6/8, etc.)
     - Energy level (calm → energetic)
     - Instrumentation (acoustic, electronic, orchestral)
     - Mood (happy, sad, dramatic, etc.)
     - Duration (precise length)
   - **Usage**:
     ```
     "Generate 2 minutes of upbeat electronic music in D minor, 128 BPM,
      with synth lead and heavy bass"
     ```

2. **`melody_generator.py`** ⭐ *NEW*
   - Generate melody lines
   - Control: scale, rhythm, complexity
   - Export as MIDI or audio

3. **`chord_progression.py`** ⭐ *NEW*
   - Generate chord progressions
   - Styles: pop, jazz, classical, etc.
   - Output: MIDI or sheet music

4. **`bass_line_generator.py`** ⭐ *NEW*
   - Generate bass lines
   - Sync to chord progression
   - Styles: funk, rock, EDM, etc.

5. **`drum_pattern_generator.py`** ⭐ *NEW*
   - Generate drum patterns
   - Genres: rock, jazz, hip-hop, EDM
   - Control: complexity, fills, variations

### Category 2: Stem Creation & Manipulation

6. **`stem_separator.py`** ⭐ *NEW*
   - Separate audio into stems (vocals, drums, bass, other)
   - Use Demucs model
   - **Usage**: "Separate this song into vocal and instrumental tracks"

7. **`stem_generator.py`** ⭐ *NEW*
   - Generate individual instrument tracks
   - Instruments: piano, guitar, drums, bass, strings, synth
   - **Usage**: "Generate a piano melody for this chord progression"

8. **`stem_mixer.py`** ⭐ *NEW*
   - Mix multiple stems
   - Control: volume, pan, EQ per stem
   - **Usage**: "Mix these 4 stems: vocals at 100%, drums at 80%, bass at 90%"

### Category 3: Arrangement & Composition

9. **`song_arranger.py`** ⭐ *NEW*
   - Arrange song structure
   - Sections: intro, verse, chorus, bridge, outro
   - **Usage**: "Arrange this as: intro (8 bars) → verse → chorus → verse → chorus → bridge → chorus → outro"

10. **`loop_creator.py`** ⭐ *NEW*
    - Create seamless loops
    - Control: length, genre, intensity
    - **Usage**: "Create a 4-bar hip-hop drum loop at 90 BPM"

11. **`song_extender.py`** ⭐ *NEW*
    - Extend music to desired length
    - Maintain style and coherence
    - **Usage**: "Extend this 30-second clip to 2 minutes"

12. **`variation_generator.py`** ⭐ *NEW*
    - Generate variations of existing music
    - Control: how different (subtle → dramatic)
    - **Usage**: "Create 3 variations of this melody, each progressively more complex"

### Category 4: Audio Effects & Processing

13. **`audio_effects.py`** ⭐ *NEW*
    - Apply effects to audio
    - Effects: reverb, delay, chorus, flanger, phaser, distortion, compression
    - **Controls per effect**:
      - Reverb: room size, decay time, wet/dry
      - Delay: time, feedback, wet/dry
      - Compression: threshold, ratio, attack, release
    - **Usage**: "Add subtle reverb and light compression to this vocal track"

14. **`equalizer.py`** ⭐ *NEW*
    - Parametric EQ with multiple bands
    - Control: frequency, gain, Q (bandwidth)
    - Presets: vocal, bass boost, treble boost, etc.
    - **Usage**: "Boost 100Hz by 3dB, cut 3kHz by 2dB"

15. **`dynamics_processor.py`** ⭐ *NEW*
    - Compression, limiting, gating
    - Per-track or master
    - **Usage**: "Apply gentle compression with 3:1 ratio, -10dB threshold"

16. **`pitch_shifter.py`** ⭐ *NEW*
    - Shift pitch without changing tempo
    - Control: semitones, cents
    - **Usage**: "Shift this melody up 2 semitones"

17. **`time_stretcher.py`** ⭐ *NEW*
    - Change tempo without changing pitch
    - Control: percentage (50%-200%)
    - **Usage**: "Slow this track to 80% speed"

### Category 5: Mastering & Finalization

18. **`mastering_suite.py`** ⭐ *NEW*
    - Professional mastering pipeline
    - Steps: EQ → compression → limiting → stereo enhancement
    - Targets: streaming, CD, vinyl
    - **Usage**: "Master this track for Spotify streaming (LUFS -14)"

19. **`loudness_normalizer.py`** ⭐ *NEW*
    - Normalize to target loudness (LUFS)
    - Standards: Spotify (-14), YouTube (-13), CD (-9)
    - **Usage**: "Normalize to -14 LUFS for streaming"

20. **`stereo_enhancer.py`** ⭐ *NEW*
    - Stereo width control
    - Mid/side processing
    - **Usage**: "Widen the stereo image by 20%"

### Category 6: Vocal Processing

21. **`vocal_tuner.py`** ⭐ *NEW*
    - Auto-tune vocals
    - Control: pitch correction strength (subtle → hard)
    - **Usage**: "Apply subtle pitch correction to this vocal"

22. **`vocal_harmonizer.py`** ⭐ *NEW*
    - Generate vocal harmonies
    - Intervals: 3rd, 5th, octave
    - **Usage**: "Add 3-part harmony to this vocal track"

23. **`voice_transformer.py`** ⭐ *NEW*
    - Transform voice characteristics
    - Change: gender, age, character (robotic, ethereal, etc.)
    - **Usage**: "Make this voice sound deeper and more robotic"

24. **`de_esser.py`** ⭐ *NEW*
    - Remove harsh sibilance (S, T sounds)
    - Control: frequency, threshold
    - **Usage**: "De-ess this vocal at 8kHz"

### Category 7: Analysis & Utilities

25. **`audio_analyzer.py`** ⭐ *NEW*
    - Analyze audio properties
    - Output: BPM, key, spectrum, loudness
    - **Usage**: "What's the BPM and key of this track?"

26. **`genre_classifier.py`** ⭐ *NEW*
    - Identify music genre
    - Confidence scores
    - **Usage**: "What genre is this music?"

27. **`audio_converter.py`** ⭐ *NEW*
    - Convert between formats
    - Formats: MP3, WAV, FLAC, OGG, AAC, M4A
    - Control: bitrate, sample rate, bit depth
    - **Usage**: "Convert to 320kbps MP3"

---

## 🎚️ Genre-Specific Presets

### Electronic Music

**EDM House**:
- Tempo: 120-130 BPM
- Key: Usually minor (Am, Dm, Em)
- Structure: Build → Drop → Break → Drop
- Instruments: Synth lead, bass, drums, pads
- Effects: Sidechain compression, reverb, delay

**Dubstep**:
- Tempo: 140 BPM (70 BPM feel)
- Sub-bass heavy
- Wobble bass synthesis
- Half-time drums

**Ambient**:
- Tempo: 60-90 BPM
- Pads, drones, textures
- Minimal percussion
- Heavy reverb and delay

### Orchestral

**Cinematic Epic**:
- Tempo: 80-100 BPM
- Orchestral instruments: strings, brass, percussion
- Build: Quiet → Massive climax
- Dynamics: Wide range

**Classical**:
- Traditional composition rules
- Authentic instrument samples
- Multiple movements

### Rock & Pop

**Rock**:
- Tempo: 110-140 BPM
- Instruments: Electric guitar, bass, drums, vocals
- Structure: Verse-Chorus-Verse-Chorus-Bridge-Chorus

**Pop**:
- Tempo: 100-130 BPM
- Catchy melodies
- Simple chord progressions (I-V-vi-IV)
- Radio-friendly mix

### Jazz

**Swing**:
- Tempo: 120-200 BPM
- Swing rhythm (triplet feel)
- Instruments: Piano, bass, drums, brass

**Smooth Jazz**:
- Tempo: 80-120 BPM
- Laid-back feel
- Saxophone, electric piano

### Hip-Hop

**Trap**:
- Tempo: 130-150 BPM
- 808 bass, hi-hats (triplets)
- Minimal melody

**Boom Bap**:
- Tempo: 85-95 BPM
- Classic drum breaks
- Sampled loops

---

## 🎼 Complete Music Production Workflows

### Workflow 1: Full Song from Scratch

**Input**: "Create a 3-minute upbeat electronic song in Am, 128 BPM"

**Steps**:
1. `chord_progression.py`: Generate Am progression (Am → F → C → G)
2. `melody_generator.py`: Create synth melody in Am
3. `bass_line_generator.py`: Generate bass line following chords
4. `drum_pattern_generator.py`: Create EDM drums at 128 BPM
5. `stem_generator.py`: Generate pad sounds
6. `song_arranger.py`: Arrange into intro-verse-chorus-verse-chorus-bridge-chorus-outro
7. `stem_mixer.py`: Mix all tracks (levels, panning)
8. `audio_effects.py`: Add sidechain compression, reverb
9. `mastering_suite.py`: Master to -14 LUFS
10. Returns: Final MP3/WAV

**Natural Language**:
```
User: "Create a 3-minute EDM track in A minor, upbeat and energetic"
AI: [Generates complete song through pipeline]
    Your track is ready!
    - Key: A minor
    - BPM: 128
    - Structure: Intro (16 bars) → Build → Drop → Break → Drop → Outro
    - Duration: 3:14
    Download: edm-track-am-128.mp3
```

### Workflow 2: Remix Existing Track

**Input**: "Remix this song into a lo-fi hip-hop version"

**Steps**:
1. `stem_separator.py`: Separate vocals, drums, bass, other
2. `audio_analyzer.py`: Detect original BPM and key
3. `time_stretcher.py`: Slow to 85 BPM (lo-fi tempo)
4. `drum_pattern_generator.py`: Generate lo-fi drums
5. `stem_generator.py`: Add lo-fi piano and vinyl crackle
6. `audio_effects.py`: Add lo-fi effects (bit crushing, vinyl noise)
7. `stem_mixer.py`: Mix new arrangement
8. `mastering_suite.py`: Master with lo-fi aesthetic
9. Returns: Remixed track

### Workflow 3: Podcast Intro Music

**Input**: "Create a 15-second podcast intro, dramatic and professional"

**Steps**:
1. `music_generator_pro.py`: Generate 15s orchestral music (dramatic)
2. `audio_effects.py`: Add subtle reverb
3. `loudness_normalizer.py`: Normalize to -16 LUFS (podcast standard)
4. `audio_converter.py`: Export as MP3
5. Returns: Podcast intro ready to use

### Workflow 4: Background Music for Video

**Input**: "Create background music for this 2-minute product video, uplifting and modern"

**Steps**:
1. `video_analyzer.py`: Analyze video length and mood
2. `music_generator_pro.py`: Generate 2min corporate pop track
3. `song_extender.py`: Ensure perfect 2:00 length
4. `audio_effects.py`: Light compression and EQ
5. `loudness_normalizer.py`: Normalize to -20 LUFS (background music level)
6. Returns: Music track ready to add to video

### Workflow 5: Stem-Based Mashup

**Input**: "Create a mashup of these 3 songs"

**Steps**:
1. `stem_separator.py`: Separate all 3 songs into stems
2. `audio_analyzer.py`: Detect BPM and key of each
3. `pitch_shifter.py`: Shift all to same key
4. `time_stretcher.py`: Match all to same BPM
5. `stem_mixer.py`: Mix selected stems (vocals from A, drums from B, bass from C)
6. `song_arranger.py`: Arrange into coherent structure
7. `mastering_suite.py`: Master final mashup
8. Returns: Mashup ready

---

## 🤖 n8n Workflow Automation (All Scenarios)

### Core n8n Workflows (30+ Workflows)

**Music Generation Workflows**:
1. `full-song-generator.json`
2. `genre-specific-music.json` (20 genre variations)
3. `loop-creator.json`
4. `stem-based-composition.json`

**Production Workflows**:
5. `mixing-pipeline.json`
6. `mastering-pipeline.json`
7. `vocal-production-chain.json`
8. `drum-processing.json`

**Batch Workflows**:
9. `batch-music-generation.json`
10. `batch-stem-separation.json`
11. `batch-format-conversion.json`
12. `batch-mastering.json`

**Content Creation Workflows**:
13. `podcast-full-production.json`
14. `video-with-music.json`
15. `social-media-audio-post.json`
16. `explainer-video-with-music.json`

**Remix & Mashup Workflows**:
17. `remix-generator.json`
18. `mashup-creator.json`
19. `cover-version-generator.json`

**Utility Workflows**:
20. `audio-analysis-batch.json`
21. `genre-classification-batch.json`
22. `quality-enhancement-pipeline.json`

### Example n8n Workflow: Full Song Production

```json
{
  "name": "Full Song Production Pipeline",
  "nodes": [
    {
      "type": "webhook",
      "name": "Trigger",
      "parameters": {
        "path": "generate-song",
        "method": "POST"
      }
    },
    {
      "type": "function",
      "name": "Parse Parameters",
      "parameters": {
        "functionCode": "// Extract genre, key, BPM, duration, mood"
      }
    },
    {
      "type": "http-request",
      "name": "Generate Chord Progression",
      "parameters": {
        "url": "http://music-tools/chord-progression",
        "method": "POST"
      }
    },
    {
      "type": "http-request",
      "name": "Generate Melody",
      "parameters": {
        "url": "http://music-tools/melody",
        "method": "POST"
      }
    },
    {
      "type": "http-request",
      "name": "Generate Bass",
      "parameters": {
        "url": "http://music-tools/bass-line",
        "method": "POST"
      }
    },
    {
      "type": "http-request",
      "name": "Generate Drums",
      "parameters": {
        "url": "http://music-tools/drum-pattern",
        "method": "POST"
      }
    },
    {
      "type": "http-request",
      "name": "Mix Stems",
      "parameters": {
        "url": "http://audio-server/mix",
        "method": "POST"
      }
    },
    {
      "type": "http-request",
      "name": "Apply Effects",
      "parameters": {
        "url": "http://audio-server/effects",
        "method": "POST"
      }
    },
    {
      "type": "http-request",
      "name": "Master Track",
      "parameters": {
        "url": "http://audio-server/master",
        "method": "POST"
      }
    },
    {
      "type": "http-request",
      "name": "Export Audio",
      "parameters": {
        "url": "http://audio-server/export",
        "method": "POST"
      }
    }
  ]
}
```

---

## 📋 Implementation Priority

### Phase 1A: Music Production Core (Week 1)

**Enable Audio Services**:
- [ ] Scale up Audio Server deployment
- [ ] Verify MusicGen, AudioLDM2 models loaded
- [ ] Test audio generation API

**Create Essential Music Tools** (Priority 1):
- [ ] `music_generator_pro.py` (genre-specific with deep controls)
- [ ] `stem_separator.py` (Demucs integration)
- [ ] `audio_effects.py` (reverb, delay, compression)
- [ ] `stem_mixer.py` (multi-track mixing)

### Phase 1B: Core n8n Workflows (Week 1)

**Create Foundation Workflows**:
- [ ] `full-song-generator.json`
- [ ] `mixing-pipeline.json`
- [ ] `podcast-production.json`
- [ ] `batch-music-generation.json`

### Phase 2: Advanced Production (Week 2)

**Production Tools**:
- [ ] `equalizer.py`
- [ ] `dynamics_processor.py`
- [ ] `mastering_suite.py`
- [ ] `loudness_normalizer.py`

**Composition Tools**:
- [ ] `melody_generator.py`
- [ ] `chord_progression.py`
- [ ] `drum_pattern_generator.py`
- [ ] `bass_line_generator.py`

**n8n Workflows**:
- [ ] `mastering-pipeline.json`
- [ ] `vocal-production-chain.json`
- [ ] `remix-generator.json`

### Phase 3: Vocal & Effects (Week 3)

**Vocal Tools**:
- [ ] `vocal_tuner.py`
- [ ] `vocal_harmonizer.py`
- [ ] `voice_transformer.py`
- [ ] `de_esser.py`

**Advanced Effects**:
- [ ] `pitch_shifter.py`
- [ ] `time_stretcher.py`
- [ ] `stereo_enhancer.py`

**n8n Workflows**:
- [ ] `cover-version-generator.json`
- [ ] `mashup-creator.json`

### Phase 4: Utilities & Analysis (Week 4)

**Utility Tools**:
- [ ] `audio_analyzer.py`
- [ ] `genre_classifier.py`
- [ ] `audio_converter.py`
- [ ] `song_extender.py`

**n8n Workflows**:
- [ ] `audio-analysis-batch.json`
- [ ] `quality-enhancement-pipeline.json`
- [ ] `batch-format-conversion.json`

---

## 🎯 Professional Use Cases

### Music Producer Workflow

"I need to create a professional EDM track for a client"

**Pipeline**:
1. Generate chord progression (Am-F-C-G)
2. Create melody with synth lead
3. Generate bass line (sub bass + mid bass)
4. Create drum pattern (kick, snare, hi-hats)
5. Add pads and atmospheric sounds
6. Arrange into full song structure (intro → build → drop → break → drop → outro)
7. Mix stems (levels, EQ, panning)
8. Add production effects (sidechain compression, reverb, delay)
9. Master to streaming standards (-14 LUFS)
10. Export in multiple formats (WAV, MP3 320kbps)

### Podcast Producer Workflow

"I need intro music, background music, and outro music for my tech podcast"

**Pipeline**:
1. Generate 15s intro (dramatic orchestral)
2. Generate 2min background loop (corporate pop, subtle)
3. Generate 10s outro (same theme as intro)
4. Normalize all to podcast levels (intro: -16 LUFS, bg: -25 LUFS, outro: -16 LUFS)
5. Export as MP3s

### Content Creator Workflow

"I need royalty-free background music for my YouTube videos"

**Pipeline**:
1. Analyze video content and mood
2. Generate appropriate genre music
3. Match exact video length
4. Normalize to YouTube standards (-13 LUFS)
5. Export and sync with video

---

**This comprehensive music production suite provides professional-grade capabilities entirely self-hosted!**
