/** Server job phases mapped onto the UI's three-step progress order. */
export type GenerationStep =
  | "processing-sources"
  | "preparing-knowledge"
  | "generating-brd"

export function mapJobPhaseToStep(phase: string | null): GenerationStep {
  switch (phase) {
    case "preparing_knowledge":
      return "preparing-knowledge"
    case "generating_brd":
      return "generating-brd"
    default:
      return "processing-sources"
  }
}
