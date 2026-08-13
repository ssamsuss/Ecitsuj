export const EVIDENCE_CODE_PATTERN = /^E[0-9]+$/;

export type EvidenceItemDraft = { code: string; kind: string; content: string };

export type ValidationErrors = {
  title?: string;
  facts?: string;
  evidenceItems?: string;
  evidenceRowErrors: Record<number, string>;
};

export function validateCaseSetup(
  title: string,
  facts: string[],
  evidenceItems: EvidenceItemDraft[]
): ValidationErrors {
  const errors: ValidationErrors = { evidenceRowErrors: {} };

  if (!title.trim()) {
    errors.title = "Title is required.";
  }

  if (facts.filter((f) => f.trim().length > 0).length === 0) {
    errors.facts = "At least one case fact is required.";
  }

  if (evidenceItems.length === 0) {
    errors.evidenceItems = "At least one evidence item is required.";
  } else {
    const seenCodes = new Set<string>();
    evidenceItems.forEach((item, index) => {
      const code = item.code.trim();
      if (!EVIDENCE_CODE_PATTERN.test(code)) {
        errors.evidenceRowErrors[index] = "Code must match the pattern E1, E2, ... (e.g. E1).";
      } else if (seenCodes.has(code)) {
        errors.evidenceRowErrors[index] = "Evidence codes must be unique.";
      } else if (!item.kind.trim()) {
        errors.evidenceRowErrors[index] = "Evidence type is required.";
      } else if (!item.content.trim()) {
        errors.evidenceRowErrors[index] = "Evidence text is required.";
      }
      seenCodes.add(code);
    });
  }

  return errors;
}

export function isValid(errors: ValidationErrors): boolean {
  return !errors.title && !errors.facts && !errors.evidenceItems && Object.keys(errors.evidenceRowErrors).length === 0;
}
