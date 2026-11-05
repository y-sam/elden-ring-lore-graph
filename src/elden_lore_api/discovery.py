# ruff: noqa: E501

from typing import Literal, TypedDict

SpoilerLevel = Literal["minimal", "base_game", "full"]


class EntryDefinition(TypedDict):
    entity_id: str
    introduction: str
    prompt: str
    next_entity_ids: list[str]


class CollectionDefinition(TypedDict):
    id: str
    title: str
    description: str
    spoiler_level: SpoilerLevel
    default_entity_id: str
    entries: list[EntryDefinition]
    recommended_collection_ids: list[str]


COLLECTIONS: tuple[CollectionDefinition, ...] = (
    {
        "id": "start.main-characters",
        "title": "Main characters",
        "description": "Meet five figures who open the major paths through the story.",
        "spoiler_level": "minimal",
        "default_entity_id": "character.tarnished",
        "entries": [
            {
                "entity_id": "character.tarnished",
                "introduction": "The Tarnished are exiles called back to the Lands Between by the guidance of Grace. The player belongs to this group and follows its search for the Elden Ring.",
                "prompt": "Who are the Tarnished?",
                "next_entity_ids": ["character.melina", "character.godfrey"],
            },
            {
                "entity_id": "character.marika",
                "introduction": "Queen Marika the Eternal is the vessel of the Elden Ring and the divine ruler at the center of the Golden Order.",
                "prompt": "Who is Queen Marika?",
                "next_entity_ids": ["artifact.elden-ring", "character.godfrey"],
            },
            {
                "entity_id": "character.melina",
                "introduction": "Melina offers the Tarnished an accord and guides their journey toward the Erdtree while pursuing a purpose of her own.",
                "prompt": "Who is Melina?",
                "next_entity_ids": ["character.tarnished", "artifact.erdtree"],
            },
            {
                "entity_id": "character.ranni",
                "introduction": "Ranni the Witch is an Empyrean whose secret path challenges the order governing the Lands Between.",
                "prompt": "Who is Ranni?",
                "next_entity_ids": ["faction.carian-royal-family", "character.blaidd"],
            },
            {
                "entity_id": "character.godfrey",
                "introduction": "Godfrey was Marika's first Elden Lord and the first leader of the warriors who later became known as Tarnished.",
                "prompt": "Who is Godfrey?",
                "next_entity_ids": ["character.marika", "character.tarnished"],
            },
        ],
        "recommended_collection_ids": ["start.main-events", "start.important-locations"],
    },
    {
        "id": "start.main-events",
        "title": "Main events",
        "description": "Follow five events that establish the central conflict.",
        "spoiler_level": "base_game",
        "default_entity_id": "event.shattering-of-the-elden-ring",
        "entries": [
            {
                "entity_id": "event.godfrey-banished",
                "introduction": "Godfrey and his warriors were stripped of Grace and banished from the Lands Between, becoming the first Tarnished.",
                "prompt": "Why was Godfrey banished?",
                "next_entity_ids": ["character.godfrey", "character.tarnished"],
            },
            {
                "entity_id": "event.night-of-black-knives",
                "introduction": "On the Night of the Black Knives, assassins stole a fragment of Destined Death and murdered Godwyn the Golden.",
                "prompt": "What happened on the Night of the Black Knives?",
                "next_entity_ids": ["character.godwyn", "artifact.rune-of-death"],
            },
            {
                "entity_id": "event.shattering-of-the-elden-ring",
                "introduction": "The Elden Ring was shattered, breaking the order it embodied and setting the central struggle of the game in motion.",
                "prompt": "What was the Shattering of the Elden Ring?",
                "next_entity_ids": ["artifact.elden-ring", "event.war-of-the-shattering"],
            },
            {
                "entity_id": "event.war-of-the-shattering",
                "introduction": "The demigods claimed Great Runes and fought a devastating war in which no lord emerged victorious.",
                "prompt": "What was the War of the Shattering?",
                "next_entity_ids": ["artifact.great-runes", "event.battle-of-aeonia"],
            },
            {
                "entity_id": "event.battle-of-aeonia",
                "introduction": "Malenia and Radahn fought to a stalemate in Caelid, where the release of Scarlet Rot transformed the region.",
                "prompt": "What happened at the Battle of Aeonia?",
                "next_entity_ids": ["character.malenia", "character.radahn"],
            },
        ],
        "recommended_collection_ids": ["start.main-characters", "start.major-powers"],
    },
    {
        "id": "start.important-locations",
        "title": "Important locations",
        "description": "Begin with the regions and strongholds that organize the journey.",
        "spoiler_level": "minimal",
        "default_entity_id": "location.lands-between",
        "entries": [
            {
                "entity_id": "location.lands-between",
                "introduction": "The Lands Between are the realm governed through the Elden Ring and the setting of the struggle to become Elden Lord.",
                "prompt": "What are the Lands Between?",
                "next_entity_ids": ["location.limgrave", "location.leyndell"],
            },
            {
                "entity_id": "location.limgrave",
                "introduction": "Limgrave is the opening region of the Tarnished's journey and the land surrounding Stormveil Castle.",
                "prompt": "What is Limgrave?",
                "next_entity_ids": ["location.stormveil-castle", "character.godrick"],
            },
            {
                "entity_id": "location.liurnia",
                "introduction": "Liurnia of the Lakes is home to the Academy of Raya Lucaria and the Carian royal tradition.",
                "prompt": "What is important about Liurnia?",
                "next_entity_ids": ["location.raya-lucaria", "faction.carian-royal-family"],
            },
            {
                "entity_id": "location.leyndell",
                "introduction": "Leyndell is the royal capital beneath the Erdtree and a center of the Golden Order's power.",
                "prompt": "What is Leyndell?",
                "next_entity_ids": ["artifact.erdtree", "character.morgott"],
            },
            {
                "entity_id": "location.caelid",
                "introduction": "Caelid is a region devastated by Scarlet Rot after the Battle of Aeonia.",
                "prompt": "What happened to Caelid?",
                "next_entity_ids": ["event.battle-of-aeonia", "concept.scarlet-rot"],
            },
        ],
        "recommended_collection_ids": ["start.main-characters", "start.main-events"],
    },
    {
        "id": "start.major-powers",
        "title": "Major powers",
        "description": "Meet the orders and powers competing to shape the world.",
        "spoiler_level": "base_game",
        "default_entity_id": "artifact.golden-order",
        "entries": [
            {
                "entity_id": "artifact.golden-order",
                "introduction": "The Golden Order is the world-order associated with Marika, the Erdtree and the Elden Ring.",
                "prompt": "What is the Golden Order?",
                "next_entity_ids": ["character.marika", "artifact.elden-ring"],
            },
            {
                "entity_id": "character.greater-will",
                "introduction": "The Greater Will is a distant cosmic power associated with the Two Fingers and the order imposed through the Elden Ring.",
                "prompt": "What is the Greater Will?",
                "next_entity_ids": ["faction.two-fingers", "artifact.elden-ring"],
            },
            {
                "entity_id": "faction.two-fingers",
                "introduction": "The Two Fingers interpret the Greater Will and guide candidates chosen to inherit divine power.",
                "prompt": "What are the Two Fingers?",
                "next_entity_ids": ["character.greater-will", "concept.empyrean"],
            },
            {
                "entity_id": "outer-god.frenzied-flame",
                "introduction": "The Frenzied Flame is a power of chaos that seeks to melt away division and return all existence to one.",
                "prompt": "What is the Frenzied Flame?",
                "next_entity_ids": ["faction.three-fingers", "character.hyetta"],
            },
            {
                "entity_id": "outer-god.formless-mother",
                "introduction": "The Formless Mother is an outer power associated with accursed blood and Mohg's dynasty.",
                "prompt": "What is the Formless Mother?",
                "next_entity_ids": ["character.mohg", "location.mohgwyn-palace"],
            },
        ],
        "recommended_collection_ids": ["start.main-events", "start.realm-of-shadow"],
    },
    {
        "id": "start.realm-of-shadow",
        "title": "Realm of Shadow",
        "description": "Enter five central threads from Shadow of the Erdtree.",
        "spoiler_level": "full",
        "default_entity_id": "location.realm-of-shadow",
        "entries": [
            {
                "entity_id": "location.realm-of-shadow",
                "introduction": "The Realm of Shadow is the hidden land entered by following Miquella beyond his cocoon.",
                "prompt": "What is the Realm of Shadow?",
                "next_entity_ids": ["character.miquella", "event.miquella-enters-shadow"],
            },
            {
                "entity_id": "character.miquella",
                "introduction": "Miquella abandons parts of himself while pursuing a path to divinity in the Realm of Shadow.",
                "prompt": "What is Miquella seeking in the Realm of Shadow?",
                "next_entity_ids": ["character.st-trina", "artifact.gate-of-divinity"],
            },
            {
                "entity_id": "character.messmer",
                "introduction": "Messmer the Impaler leads Marika's concealed crusade against the peoples of the Realm of Shadow.",
                "prompt": "Who is Messmer?",
                "next_entity_ids": ["event.messmers-crusade", "faction.hornsent"],
            },
            {
                "entity_id": "character.metyr",
                "introduction": "Metyr, Mother of Fingers, is the progenitor of the finger creatures and central to the history of their guidance.",
                "prompt": "Who is Metyr?",
                "next_entity_ids": ["character.ymir", "location.cathedral-manus-metyr"],
            },
            {
                "entity_id": "people.shamans",
                "introduction": "The Shamans were Marika's people in the Hinterland and were persecuted by the Hornsent culture.",
                "prompt": "Who were Marika's Shamans?",
                "next_entity_ids": ["character.marika", "location.shaman-village"],
            },
        ],
        "recommended_collection_ids": ["start.major-powers", "start.main-characters"],
    },
)


COLLECTION_BY_ID = {collection["id"]: collection for collection in COLLECTIONS}


def spoiler_rank(level: SpoilerLevel) -> int:
    return {"minimal": 0, "base_game": 1, "full": 2}[level]
