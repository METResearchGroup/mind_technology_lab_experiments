from typing import Dict, List, Tuple


def get_concept_pairs() -> Dict[str, List[Tuple[str, str]]]:
    return {
        "Fairness": [
            ("This policy treats everyone equally.", "This policy unfairly favors one group."),
            ("The decision was impartial and just.", "The decision was biased and unjust."),
            ("The process was transparent and fair.", "The process was opaque and unfair."),
            ("Everyone received the same opportunity.", "Some people were denied a fair chance."),
            ("Resources were allocated based on need.", "Resources were allocated based on favoritism."),
            ("The referee enforced the rules consistently.", "The referee enforced the rules inconsistently."),
            ("The grading rubric was applied evenly.", "The grading rubric was applied unevenly."),
            ("Compensation was equitable across roles.", "Compensation was unequal for similar roles."),
        ],
        "Feelings": [
            ("I feel sad and anxious about this.", "I feel nothing about this."),
            ("Their response showed empathy and care.", "Their response was cold and unfeeling."),
            ("She expressed joy and gratitude.", "She showed no emotion or reaction."),
            ("He was visibly angry and frustrated.", "He appeared detached and indifferent."),
            ("They felt ashamed and remorseful.", "They felt nothing about their actions."),
            ("Her words conveyed compassion.", "Her words lacked any warmth."),
            ("The group shared excitement and hope.", "The group showed no emotional reaction."),
            ("He was fearful and uncertain.", "He showed no sign of fear or uncertainty."),
        ],
        "Harms": [
            ("This action causes harm to others.", "This action does not harm anyone."),
            ("The proposal risks hurting vulnerable people.", "The proposal poses no harm."),
            ("His behavior inflicted damage and distress.", "His behavior caused no damage."),
            ("The policy increases the risk of injury.", "The policy does not increase any risk."),
            ("Their decision led to social harm.", "Their decision avoided social harm."),
            ("This product can cause health issues.", "This product carries no health risks."),
            ("The act results in financial loss to others.", "The act does not cause financial loss."),
            ("It creates psychological distress.", "It does not create psychological distress."),
        ],
        "Honesty": [
            ("He told the truth clearly.", "He lied about the facts."),
            ("Her statement was honest and accurate.", "Her statement was dishonest and misleading."),
            ("They were transparent and truthful.", "They were deceptive and untruthful."),
            ("He admitted his mistake openly.", "He concealed his mistake."),
            ("She gave a candid account of events.", "She fabricated an account of events."),
            ("Their reporting was factual and sincere.", "Their reporting was false and insincere."),
            ("He refused to deceive the audience.", "He chose to deceive the audience."),
            ("The response was forthright.", "The response was evasive."),
        ],
        "Relational Obligation": [
            ("She helped her friend because of their bond.", "She ignored her friend's needs."),
            ("He fulfilled his duty to his family.", "He neglected his duty to his family."),
            ("They honored their commitment to the team.", "They abandoned their commitment."),
            ("She supported her partner during hardship.", "She abandoned her partner during hardship."),
            ("He took care of his parents as promised.", "He failed to care for his parents as promised."),
            ("They stood by their colleague loyally.", "They disregarded their colleague."),
            ("He repaid the favor he was owed.", "He refused to repay the favor."),
            ("She checked in on her friend regularly.", "She never checked in on her friend."),
        ],
        "Social Norms": [
            ("He followed the community's rules.", "He violated the community's rules."),
            ("Their behavior aligned with social expectations.", "Their behavior broke social expectations."),
            ("She acted appropriately in public.", "She acted inappropriately in public."),
            ("He respected quiet hours in the building.", "He ignored quiet hours in the building."),
            ("They queued patiently and waited their turn.", "They cut in line without waiting."),
            ("She dressed according to the event's etiquette.", "She ignored the event's etiquette."),
            ("He used polite language with strangers.", "He used rude language with strangers."),
            ("They complied with safety guidelines.", "They disregarded safety guidelines."),
        ],
    }


