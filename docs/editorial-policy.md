# Editorial and source policy

This policy applies to the base game and *Shadow of the Erdtree*. English is
the canonical editorial language. Spanish and Brazilian Portuguese are added,
in that order, as reviewed localizations of project-authored text.

During the current development phase, English is the only language required
for content-completeness and release gates. Existing Spanish and Brazilian
Portuguese drafts remain stored, but their final human review resumes closer
to public production launch.

The project is an unofficial knowledge graph. It must not become a substitute
for the games or a redistribution archive for protected text, artwork, audio,
video, maps, fonts, logos, or other assets.

## Claim classification

Every claim uses exactly one evidence level:

| Value | Meaning |
| --- | --- |
| `explicit` | A primary source states the claim directly. |
| `synthesis` | The claim directly combines two or more explicit statements. |
| `strong_inference` | Primary evidence strongly supports, but does not state, the claim. |
| `weak_inference` | The interpretation is plausible but has material gaps. |
| `theory` | An editorial or community theory. |
| `disputed` | Relevant evidence supports incompatible readings. |
| `unknown` | Available evidence is insufficient. |

`confidence` is `high`, `medium`, or `low`; numeric confidence is prohibited.
`review_status` is `draft`, `reviewed`, `disputed`, or `rejected`.

Editorial approval and verification strength are separate. `verification_status`
is one of:

| Value | Meaning |
| --- | --- |
| `unverified` | No editor has recorded an external comparison. |
| `community_verified` | Compared with a named secondary/community reference, with its URL recorded. |
| `official_verified` | Compared with a first-party publication. |
| `game_verified` | Compared directly with observable in-game content; highest status. |

A claim cannot have a stronger verification status than all evidence supporting
it. Community verification may be sufficient for `reviewed`, but it never
receives the highest verification badge and should be upgraded when a direct
game comparison becomes available.

Answers lead with explicit evidence. Inferences are qualified, theories appear
in a separate section, contradictions are preserved, and insufficient evidence
must result in an explicit “unknown” rather than a guessed answer.

## Source hierarchy

Authority and reuse permission are separate fields.

1. `P0_GAME`: observable game content: item descriptions, dialogue, cutscenes,
   quests, maps, and world state.
2. `P1_OFFICIAL`: official sites, manuals, patch notes, guides, and releases.
3. `P2_CREATOR`: attributable statements by creators or the development team.
4. `S1_SECONDARY`: analysis that points to specific primary evidence.
5. `T_COMMUNITY`: community interpretations and theories.

Secondary and established fan-maintained sources, including the Elden Ring
Fandom wiki, may support editorial approval at `community_verified`. They are
reference-only: the project stores the URL and an original summary, never copied
wiki text or a wiki database. Community verification does not establish the
highest canonical status and is superseded by a direct game or official-source
comparison.

Structural readiness is not editorial approval. A human editor must open the
verification source, ensure the project-authored summary does not overstate it,
and review evidence before dependent claims. Automated import never changes
`draft` to `reviewed`. Existing reviewed records whose source is `P0_GAME` or
`P1_OFFICIAL` are normalized to `game_verified` and `official_verified`,
respectively, during import.

## Copyright-safe storage

Public project data may contain:

- facts, relationships, stable identifiers, and source metadata;
- precise locators such as item name, NPC, quest stage, or cutscene;
- original summaries and analysis written for this project;
- links and attribution.

Public project data must not contain by default:

- complete or systematic game text or extracted game files;
- copied wiki text or databases;
- screenshots, maps, icons, logos, fonts, audio, or video;
- embeddings made from material whose use is not authorized.

Verbatim quotations are disabled for the initial release. Any later exception
requires manual review, direct analytical necessity, attribution, and the
smallest useful fragment. An internal target such as 15–20 words is a product
limit, not a legal safe harbor.

No source may be embedded, publicly displayed, or sent to an external model
unless its rights metadata explicitly allows that operation.

## Rights metadata

Each source records:

```text
rights_status: original | public_domain | permissive_license |
               reference_only | permission_granted | unknown
license
attribution
terms_url
retrieved_at
ingestion_allowed
public_display_allowed
embedding_allowed
```

`unknown` fails closed: ingestion, public display, and embedding are prohibited.

## Localization

- Claims and relationships are language-neutral.
- English names and project-authored summaries are canonical internally.
- Spanish is the first optional localization; Brazilian Portuguese is second.
- Machine-assisted translations remain `draft` until human review.
- A translated quotation is never presented as an official localization.
- Official localized names require verification in that game language.

## Branding

Use an original interface and original or permissively licensed visual assets.
Do not use official logos or imply endorsement. Public pages must display:

> Unofficial fan project. Not affiliated with or endorsed by FromSoftware or
> Bandai Namco Entertainment. Elden Ring and related names are trademarks of
> their respective owners.
