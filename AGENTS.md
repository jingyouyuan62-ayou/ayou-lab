# Ayou-Lab Project Instructions

These are long-term project-level rules for Codex working inside Ayou-Lab.
They describe what the project is, what it is becoming, and how work should be done.
Read them before making changes.

## 1. Project Positioning

Ayou-Lab is a growing personal visual archive and visual laboratory.
It is not intended to be a conventional portfolio.

Core idea:

> "A collection of things I can't explain why I like."

Long-term goal:

> "Ayou-Lab doesn't just remember what I like. It uses what I like to make something new."

The project records how one person sees the world and gradually turns accumulated visual
experience into something that can be understood, searched, recombined, and used for creation.

## 2. Project Roadmap

The long-term roadmap has three phases.

### Phase 1 — Archive

Build a real personal visual archive.

- Images are the primary material.
- The archive should eventually contain dozens, hundreds, or thousands of visual references.
- Do not force every image into rigid categories merely for organizational convenience.
- Images the user likes for unclear or intuitive reasons are valuable.

### Phase 2 — Understanding

AI analyzes archived images into structured visual information.

Potential dimensions include: content, composition, color, texture, material, spatial depth,
visual hierarchy, mood, visual style, Visual DNA, interaction possibilities, uncertainty.

- AI interpretation is not automatically treated as fact.
- Keep uncertainty visible when appropriate.
- The user's own interpretation is a separate layer from AI analysis.

An important future field is **Echoes**: personal associations triggered by an image, such as
paintings, films, music, objects, places, memories, or other visual references.

- AI may suggest possible Echoes.
- The user has final authority over whether an association belongs to the archive.

### Phase 3 — Creation

Eventually Ayou-Lab should be able to use accumulated archive material as creative raw material.

Potential workflow:

Archive elements → select several elements → choose a Visual Recipe → recombine / generate
→ save the result back into the archive

- The system should use the user's accumulated visual memory rather than generating generic
  aesthetic content unrelated to the archive.
- Do not implement Phase 3 unless explicitly requested.

## 3. Current Visual DNA

The current working Visual DNA is: NATURE, MEMORY, STRANGE, COLOR, DREAM.

This is a working interpretation, not a permanently fixed taxonomy.
Do not force future images into these categories if they do not fit.

Current aesthetic direction includes: nature; memory; lived-in warmth; vintage qualities;
unusual or surreal moments; strong color; dreamy imagery; nostalgic internet / Y2K influences;
illustration and collage; organic forms; imperfect or irregular elements.

Avoid reducing the aesthetic to: generic Japanese minimalism; pure MUJI style; generic Pinterest
aesthetics; generic "dreamy" AI imagery.

The site should preserve tension between order and irregularity.

## 4. Current Technical Architecture

The current implementation is intentionally simple: HTML, CSS, JavaScript, JSON.

Do not introduce a framework, backend, database, CMS, or unnecessary build system unless
explicitly requested.

Current important files and folders:

- `index.html`
- `archive.html`
- `style.css`
- `archive.js`
- `data/entries.json`
- `images/`

The archive mechanism should remain data-driven:

image file + structured entry data → Archive page

When possible, adding a new archive image should not require manually duplicating HTML cards.

## 5. Collaboration Model

The user is the project owner and creative director.

The user provides: project direction, ideas, aesthetic judgment, content, images, and final
visual decisions.

Codex is responsible for: technical analysis, implementation, code, debugging, testing, Git,
technical architecture, and explaining technical decisions in understandable language.

- When the user describes WHAT they want, Codex should determine HOW to implement it, unless the
  user explicitly specifies the technical method.
- Do not require the user to make technical decisions they are not qualified to make.
- Explain important technical decisions in plain language after implementation.

## 6. Development Workflow

Work incrementally. Preferred workflow:

analysis → minimal implementation → test → report → user review → next iteration

Do not unnecessarily rebuild the whole project when a small change is sufficient.

Before modifying files:

1. inspect the current project state
2. identify relevant files
3. explain the intended change briefly when the task is non-trivial
4. make the smallest appropriate change
5. test the result

- Do not remove existing working functionality without a reason.
- Preserve the established visual language unless the user explicitly asks for a redesign.

## 7. Image Analysis Workflow

When using image understanding tools:

- Prefer processing one image at a time.
- Do not unnecessarily call multiple image-viewing tools in parallel.
- Do not combine image viewing with unrelated tool operations when avoidable.
- After successfully reading an image, analyze what is actually visible.
- Distinguish observation from interpretation.
- Mark uncertainty where the image does not provide enough evidence.

If an image-tool call produces `"No tool output found for tool call ..."`:

- Do not repeatedly retry the same failed conversation state.
- Stop and report the tool failure.
- If the issue appears to be caused by conversation/tool-call state, recommend starting a fresh
  conversation rather than repeatedly corrupting the same thread.

Do not modify Ayou-Lab files merely to fix an external model/tool-call failure.

## 8. Archive Data

Archive entries should eventually support more than basic image metadata.

Possible layers include: image, title, date, source, medium, tags, note, AI visual analysis,
Visual DNA, Echoes, user interpretation, uncertainty / confidence.

- Do not assume AI-generated metadata is automatically correct.
- Do not permanently lock the taxonomy too early.

## 9. Current Development Priority

Current priority: Phase 1 — Archive, while gradually preparing for Phase 2 — Understanding.

Do not currently build:

- complex animation
- backend
- database
- CMS
- authentication
- complicated upload systems
- Phase 3 creation system
- unnecessary framework infrastructure

Advanced visual effects for individual images should be treated as later experiments rather than
blocking the core archive architecture.

## 10. Visual Design Principle

The existing Ayou-Lab visual language should be treated as an established starting point:

- warm gray / off-white background
- dark text
- large typography
- serif body text where appropriate
- restrained color
- generous whitespace
- editorial / archive feeling
- controlled irregularity

Do not automatically make the site more polished, corporate, futuristic, or generic.
The website should feel like a living personal visual archive rather than a commercial portfolio.

## 11. Decision Principle

When technical convenience conflicts with the project's long-term identity, prioritize the
project's stated purpose.

When there are multiple technically valid approaches:

1. prefer the simplest reliable solution
2. avoid unnecessary dependencies
3. preserve future extensibility
4. explain the trade-offs

Do not over-engineer early stages.
