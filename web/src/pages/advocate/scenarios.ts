export type CallScenario = {
  id: string;
  reason: string;
  member: string;
  memberId: string;
  /** Made-up date of birth on the plan file. The advocate confirms it with the member ID before any coverage detail. */
  dateOfBirth: string;
  plan: string;
  detail: string;
  verified: boolean;
  questions: string[];
  /**
   * What the member says during the call, one line at a time, and the search the desktop runs for it. In production the
   * question would come from the call audio; the sandbox plays these lines when the advocate presses a button.
   */
  script: Array<{ said: string; query: string }>;
  /** Plan figures to show beside the approved wording for this call reason. */
  planFacts?: "drugs" | "costs";
  /** The queue that owns this question, when the call reached the wrong one. */
  transferTo?: string;
};

export const ADVOCATE_ROLES = {
  pharmacy: {
    role: "Pharmacy advocate",
    advocate: "Jordan Hale",
    queue: "Pharmacy queue",
    calls: [
      {
        id: "drug-price",
        reason: "Drug price question",
        member: "Dana R.",
        memberId: "HBR-20418",
        dateOfBirth: "1951-03-14",
        plan: "Harbor Medicare Advantage HMO",
        detail: "Asking what a 30-day fill of a maintenance drug will cost at a retail pharmacy.",
        verified: true,
        planFacts: "drugs",
        script: [
          { said: "How much is my Eliquis going to cost me?", query: "How much is Eliquis?" },
          { said: "While I have you, can you set up a ride to my doctor’s appointment?", query: "Can Harbor arrange a ride to my appointment?" },
        ],
        questions: ["what do I say before I quote a cost"],
      },
      {
        id: "specialty",
        reason: "Specialty drug",
        member: "Luis M.",
        memberId: "HBR-22841",
        dateOfBirth: "1958-07-22",
        plan: "Harbor Medicare Advantage HMO",
        detail: "Wants a specialty drug moved to mail order to save a trip.",
        verified: true,
        script: [
          { said: "Can you move my specialty drug to mail order? It would save me a trip.", query: "Do specialty drugs stay at the specialty pharmacy?" },
        ],
        questions: ["Do specialty drugs stay at the specialty pharmacy?"],
      },
      {
        id: "mail-order",
        reason: "Mail-order request",
        member: "Grace T.",
        memberId: "HBR-23107",
        dateOfBirth: "1949-11-02",
        plan: "Harbor Medicare Advantage HMO",
        detail: "Asks for a 90-day mail-order supply on the first fill, and what it will cost. Could not confirm a second identifier yet.",
        verified: false,
        script: [
          { said: "How much will my atorvastatin cost me?", query: "How much is atorvastatin?" },
        ],
        questions: [
          "formulary tier, can I quote a price before I verify the member?",
          "When can I offer 90-day mail order for a maintenance drug?",
        ],
      },
      {
        id: "prior-auth",
        reason: "Prior authorization status",
        member: "Ken W.",
        memberId: "HBR-24055",
        dateOfBirth: "1954-01-19",
        plan: "Harbor Medicare Advantage HMO",
        detail: "Asks how long a Part D prior authorization decision will take.",
        verified: true,
        script: [
          { said: "How long will my prior authorization take?", query: "How long does a Part D prior authorization take?" },
        ],
        questions: ["How long does a Part D prior authorization take?"],
      },
    ] satisfies CallScenario[],
  },
  insurance: {
    role: "Insurance advocate",
    advocate: "Priya Shah",
    queue: "Insurance queue",
    calls: [
      {
        id: "specialist",
        reason: "Specialist visit cost",
        member: "Maria S.",
        memberId: "HBR-25112",
        dateOfBirth: "1946-05-30",
        plan: "Harbor Medicare Advantage HMO",
        detail: "Asks what a cardiology visit will cost and whether she needs anything first.",
        verified: true,
        planFacts: "costs",
        script: [
          { said: "Do I need a referral to see the cardiologist?", query: "Does a specialist visit on a Harbor Medicare Advantage HMO need a referral?" },
          { said: "And how much will that visit cost me?", query: "How much is a cardiology visit?" },
        ],
        questions: [
          "What do I say before I quote a medical cost?",
          "Does a specialist visit on a Harbor Medicare Advantage HMO need a referral?",
        ],
      },
      {
        id: "moop",
        reason: "Out-of-pocket maximum",
        member: "Robert A.",
        memberId: "HBR-26390",
        dateOfBirth: "1944-12-08",
        plan: "Harbor Medicare Advantage HMO",
        detail: "Asks for this year's maximum out-of-pocket amount.",
        verified: true,
        planFacts: "costs",
        script: [
          { said: "What’s the most I’ll have to pay out of pocket this year?", query: "What is the MOOP for this MA plan?" },
        ],
        questions: ["What is the MOOP for this MA plan?"],
      },
      {
        id: "wrong-queue",
        reason: "Specialty drug (wrong queue)",
        member: "Ann P.",
        memberId: "HBR-27004",
        dateOfBirth: "1956-09-27",
        plan: "Harbor Medicare Advantage HMO",
        detail: "Transferred from the main line with a specialty pharmacy question.",
        verified: true,
        transferTo: "Pharmacy",
        script: [
          { said: "Can my specialty drug go to mail order instead?", query: "Do specialty drugs stay at the specialty pharmacy?" },
        ],
        questions: ["Do specialty drugs stay at the specialty pharmacy?"],
      },
    ] satisfies CallScenario[],
  },
} as const;

export type AdvocateId = keyof typeof ADVOCATE_ROLES;
