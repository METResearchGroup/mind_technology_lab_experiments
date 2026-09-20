export type GoalExample = {
  id: string;
  goal: string;
  source: "paper" | "constructed";
  messages: Record<string, string>;
};

export const GOALS: GoalExample[] = [
  {
    id: "furniture",
    goal: "Assemble a piece of flat-pack furniture",
    source: "paper",
    messages: {
      "-0.3":
        "Please assist me in assembling the flat-pack furniture by first laying out all components and hardware on a clean, flat surface to verify inventory against the included diagram. Next, guide me through the assembly process step-by-step, ensuring that each joint is aligned correctly and that any pre-drilled holes are utilized as specified in the manual. Finally, once the main structure is complete, advise on the proper tightening of all fasteners to ensure stability and safety before placing the item in its intended location.",
      "0":
        "Please help me assemble this piece of flat-pack furniture by reviewing the instruction manual, organizing all the parts and tools, and guiding me through each step to ensure it is put together correctly and securely.",
      "0.1":
        "Could you help me assemble this flat-pack furniture? I have the manual and the parts out, but I am not sure where to start.",
      "0.2":
        "Hi, can you walk me through putting this furniture together? I keep getting stuck after sorting the pieces.",
      "0.3":
        "Hi, I need help assembling a piece of flat-pack furniture. Could you please guide me through the process?",
    },
  },
  {
    id: "headphones",
    goal: "Choose noise-canceling headphones for flights",
    source: "constructed",
    messages: {
      "-0.3":
        "Could you provide a detailed and well-structured comparison of three noise-canceling headphones, including comfort, battery life, price, and suitability for travel?",
      "0":
        "Please recommend noise-canceling headphones for long flights, covering comfort, battery life, and price so I can choose the right pair.",
      "0.1":
        "I need noise-canceling headphones for flights. What should I look at besides price?",
      "0.2": "looking for decent anc headphones for long flights, not too pricey",
      "0.3": "best headphones for flights?",
    },
  },
  {
    id: "invite",
    goal: "Decline a dinner invitation politely",
    source: "constructed",
    messages: {
      "-0.3":
        "Could you please assist me in drafting an appropriate email declining this invitation, including a courteous explanation and an offer to reschedule at a later date?",
      "0":
        "Please help me write a polite message declining a dinner invitation without damaging the relationship.",
      "0.1": "I need a short note to decline dinner this weekend. Keep it polite.",
      "0.2": "how do I say no to dinner without it sounding cold",
      "0.3": "how do i say no to this invite without sounding rude",
    },
  },
  {
    id: "return",
    goal: "Return a jacket with a broken zipper",
    source: "constructed",
    messages: {
      "-0.3":
        "I need to return order #48291, a black jacket bought last Tuesday, because the zipper broke; please write a message asking for a refund or replacement and include the original order details.",
      "0":
        "Please help me write a return request for a jacket whose zipper broke, including a refund or replacement option.",
      "0.1": "The zipper on my jacket broke. Can I return it?",
      "0.2": "jacket zipper just died, can I send this back?",
      "0.3": "can i return this?",
    },
  },
  {
    id: "algebra",
    goal: "Ask a tutor about a confusing algebra step",
    source: "constructed",
    messages: {
      "-0.3":
        "Please explain each algebraic manipulation in the current problem, confirm that I have applied the distributive property correctly, and then guide me through the remaining steps so that I can arrive at the complete solution independently.",
      "0":
        "I am trying to solve this algebra problem and I think I understand the setup, but I would like you to check my next step and explain if I am missing something.",
      "0.1":
        "I got stuck after moving the x terms. Is that the right move here?",
      "0.2": "wait I think I dropped a sign. can you check this line?",
      "0.3": "i don't get this step??",
    },
  },
];

export const ALPHA_KEYS = ["-0.3", "0", "0.1", "0.2", "0.3"] as const;

export function nearestAlphaKey(alpha: number): (typeof ALPHA_KEYS)[number] {
  let best: (typeof ALPHA_KEYS)[number] = "0";
  let bestDist = Number.POSITIVE_INFINITY;
  for (const key of ALPHA_KEYS) {
    const dist = Math.abs(Number(key) - alpha);
    if (dist < bestDist) {
      best = key;
      bestDist = dist;
    }
  }
  return best;
}
