import { useCallback, useState } from "react";

export function useFlash() {
  const [noteKey, setNoteKey] = useState(0);

  const show = useCallback(() => {
    setNoteKey((current) => current + 1);
  }, []);

  return [noteKey, show] as const;
}
