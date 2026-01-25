/**
 * @description 考试计分引擎
 */

export type DeductionRecord = {
    stepId: string;
    reason: string;
    score: number;
};

export type ScoringState = {
    currentScore: number;
    deductions: DeductionRecord[];
    finalized: boolean;
    fatalReasonCode?: string;
};

type Listener = (state: ScoringState) => void;

const listeners = new Set<Listener>();

let state: ScoringState = {
    currentScore: 100,
    deductions: [],
    finalized: false,
};

function emit(): void {
    listeners.forEach((listener) => listener({ ...state, deductions: [...state.deductions] }));
}

export const scoringEngine = {
    reset(initialScore = 100): void {
        state = {
            currentScore: initialScore,
            deductions: [],
            finalized: false,
        };
        emit();
    },

    getState(): ScoringState {
        return { ...state, deductions: [...state.deductions] };
    },

    deduct(stepId: string, reason: string, score: number): ScoringState {
        const deduction = { stepId, reason, score };
        state = {
            ...state,
            currentScore: Math.max(0, state.currentScore - score),
            deductions: [...state.deductions, deduction],
        };
        emit();
        return this.getState();
    },

    finalize(fatalReasonCode?: string): ScoringState {
        state = {
            ...state,
            finalized: true,
            fatalReasonCode,
        };
        emit();
        return this.getState();
    },

    subscribe(listener: Listener): () => void {
        listeners.add(listener);
        return () => {
            listeners.delete(listener);
        };
    },
};
