import { useCallback, useEffect, useRef, useState } from "react";

export type BRDData = {
  executive_summary: {
    content: string;
  };

  project_overview: {
    project_name: string;
    description: string;
  };

  business_objectives: {
    objectives: string[];
  };

  scope: {
    in_scope: string[];
    out_of_scope: string[];
  };

  stakeholders: {
    stakeholders: {
      name: string;
      role: string | null;
      organization: string | null;
    }[];
  };

  business_requirements: {
    requirements: string[];
  };

  functional_requirements: {
    requirements: string[];
  };

  non_functional_requirements: {
    requirements: string[];
  };

  assumptions_and_constraints: {
    assumptions: string[];
    constraints: string[];
  };

  risks_and_decisions: {
    risks: string[];
    decisions: string[];
  };

  open_questions: {
    questions: string[];
  };
};

type BRDMeta = {
  createdAt: string;
  updatedAt: string;
  userEditedAt: string | null;
};

type BRDViewerProps = {
  data: BRDData;
  meta?: BRDMeta;
  onSave: (data: BRDData) => Promise<void>;
  isSaving: boolean;
  saveFailed?: boolean;
};

function formatDocDate(value: string): string {
  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return "";
  }

  return parsed.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

type EditingSection =
  | "executive_summary"
  | "project_overview"
  | "business_objectives"
  | "scope"
  | "stakeholders"
  | "business_requirements"
  | "functional_requirements"
  | "non_functional_requirements"
  | "assumptions_and_constraints"
  | "risks_and_decisions"
   | "open_questions"
   | null;

// Idle time after the last keystroke before the draft autosaves.
const AUTOSAVE_DELAY_MS = 750;

function Section({
  number,
  title,
  isEditing,
  onEdit,
  onCancel,
  onSave,
  isSaving,
  saveFailed,
  autosaveText = null,
  children,
}: {
  number: number;
  title: string;
  isEditing: boolean;
  onEdit: () => void;
  onCancel: () => void;
  onSave: () => void;
  isSaving: boolean;
  saveFailed: boolean;
  autosaveText?: string | null;
  children: React.ReactNode;
}) {
  return (
    <section className="border-t border-hairline-soft py-8 first:border-t-0 first:pt-0">
      <div className="mb-4 flex items-center justify-between gap-4">
        <h2 className="text-2xl leading-8 font-semibold text-ink">
          <span className="mr-3 text-sm font-semibold text-stone">
            {String(number).padStart(2, "0")}
          </span>
          {title}
        </h2>

        {!isEditing && (
          <button
            type="button"
            onClick={onEdit}
            className="shrink-0 rounded-full border border-hairline bg-canvas px-4 py-1.5 text-sm font-medium text-ink transition-colors duration-200 print:hidden hover:bg-black/5"
          >
            Edit
          </button>
        )}
      </div>

      {children}

      {saveFailed && !isSaving && (
        <p className="mt-4 text-sm text-ink" role="alert">
          Couldn&apos;t save. Try again.
        </p>
      )}

      {isEditing && (
        <div className="mt-6 flex items-center justify-between gap-3 border-t border-hairline-soft pt-5 print:hidden">
          <span aria-live="polite" className="text-xs leading-5 text-stone">
            {autosaveText ?? ""}
          </span>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onCancel}
              disabled={isSaving}
              className="rounded-full border border-hairline bg-canvas px-4 py-1.5 text-sm font-medium text-ink transition-colors duration-200 hover:bg-black/5 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Cancel
            </button>

            <button
              type="button"
              onClick={onSave}
              disabled={isSaving}
              className="rounded-full bg-primary px-5 py-1.5 text-sm font-semibold text-white transition-colors duration-200 hover:bg-primary-deep active:bg-primary-deep disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isSaving ? "Saving..." : "Save"}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

function BulletList({ items }: { items: string[] }) {
  if (items.length === 0) {
    return (
      <p className="text-[15px] text-steel italic">
        None specified.
      </p>
    );
  }

  return (
    <ul className="space-y-3 pl-5 text-justify text-[15px] leading-7 text-ink">
      {items.map((item, index) => (
        <li key={index} className="list-disc pl-1 marker:text-steel">
          {item}
        </li>
      ))}
    </ul>
  );
}

function EditableList({
  items,
  onChange,
  placeholder,
}: {
  items: string[];
  onChange: (items: string[]) => void;
  placeholder: string;
}) {
  function updateItem(index: number, value: string) {
    const updatedItems = [...items];
    updatedItems[index] = value;
    onChange(updatedItems);
  }

  function removeItem(index: number) {
    onChange(items.filter((_, itemIndex) => itemIndex !== index));
  }

  function addItem() {
    onChange([...items, ""]);
  }

  return (
    <div className="space-y-3">
      {items.map((item, index) => (
        <div key={index} className="flex items-start gap-2">
          <textarea
            value={item}
            onChange={(event) => updateItem(index, event.target.value)}
            placeholder={placeholder}
            rows={2}
            className="min-h-[72px] flex-1 resize-y rounded-lg border border-hairline bg-canvas px-4 py-3 text-sm leading-6 text-ink outline-none transition-colors placeholder:text-stone focus-visible:border-ink"
          />

          <button
            type="button"
            onClick={() => removeItem(index)}
            className="rounded-full border border-hairline px-4 py-2 text-[13px] font-medium text-steel transition-colors hover:bg-primary/5 hover:text-ink"
          >
            Remove
          </button>
        </div>
      ))}

      <button
        type="button"
        onClick={addItem}
        className="rounded-full border border-hairline px-5 py-2 text-[13px] font-medium text-ink transition-colors hover:bg-primary/5"
      >
        + Add item
      </button>
    </div>
  );
}

function EditableField({
  label,
  value,
  onChange,
  multiline = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  multiline?: boolean;
}) {
  return (
    <div>
      <label className="text-sm font-medium text-ink">
        {label}
      </label>

      {multiline ? (
        <textarea
          value={value}
          onChange={(event) => onChange(event.target.value)}
          rows={5}
          className="mt-2 w-full resize-y rounded-lg border border-hairline bg-canvas px-4 py-3 text-sm leading-6 text-ink outline-none transition-colors placeholder:text-stone focus-visible:border-ink"
        />
      ) : (
        <input
          type="text"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="mt-2 w-full rounded-lg border border-hairline bg-canvas px-4 py-3 text-sm leading-6 text-ink outline-none transition-colors placeholder:text-stone focus-visible:border-ink"
        />
      )}
    </div>
  );
}

export function BRDViewer({
  data,
  meta,
  onSave,
  isSaving,
  saveFailed = false,
}: BRDViewerProps) {
  const generatedOn = meta ? formatDocDate(meta.createdAt) : "";
  const updatedOn = meta ? formatDocDate(meta.updatedAt) : "";
  const editedByUser = Boolean(meta?.userEditedAt);
  const [draft, setDraft] = useState<BRDData>(data);

  const [editingSection, setEditingSection] =
    useState<EditingSection>(null);

  // Autosave (additive): persists the draft through the same onSave path
  // as the Save button, without closing the editor. Manual Save/Cancel
  // semantics are unchanged.
  const [autosavedAt, setAutosavedAt] = useState<string | null>(null);
  // State mirror of the last persisted draft, for render-safe dirty
  // checks (draft !== savedDraft means the user typed since the save).
  const [savedDraft, setSavedDraft] = useState<BRDData>(data);
  const draftRef = useRef(draft);
  const editingSectionRef = useRef(editingSection);
  const onSaveRef = useRef(onSave);
  const isSavingRef = useRef(isSaving);
  // Reference-equality base: the exact draft object last persisted
  // (or the server data when editing starts). Any new object means
  // the user typed since the last save.
  const lastSavedRef = useRef<BRDData>(data);
  const autosaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );
  const saveSeqRef = useRef(0);

  function cancelPendingAutosave() {
    if (autosaveTimerRef.current !== null) {
      clearTimeout(autosaveTimerRef.current);
      autosaveTimerRef.current = null;
    }

    saveSeqRef.current += 1;
  }

  // Saves the current draft if dirty. Never closes the editor.
  // Returns true when there was nothing to save or the save succeeded.
  const flushAutosave = useCallback(async (): Promise<boolean> => {
    if (autosaveTimerRef.current !== null) {
      clearTimeout(autosaveTimerRef.current);
      autosaveTimerRef.current = null;
    }

    const seq = saveSeqRef.current + 1;
    saveSeqRef.current = seq;

    if (
      editingSectionRef.current === null ||
      draftRef.current === lastSavedRef.current
    ) {
      return true;
    }

    if (isSavingRef.current) {
      return false;
    }

    try {
      await onSaveRef.current(draftRef.current);

      if (seq === saveSeqRef.current) {
        lastSavedRef.current = draftRef.current;
        setSavedDraft(draftRef.current);
        setAutosavedAt(
          new Date().toLocaleTimeString(undefined, {
            hour: "numeric",
            minute: "2-digit",
          }),
        );
      }

      return true;
    } catch {
      return false;
    }
  }, []);

  // Mirror latest values for timer/event-handler use. Declared before
  // the debounce effect so refs are fresh whenever it schedules.
  useEffect(() => {
    draftRef.current = draft;
    editingSectionRef.current = editingSection;
    onSaveRef.current = onSave;
    isSavingRef.current = isSaving;
  });

  // Debounce: schedule a save AUTOSAVE_DELAY_MS after the user stops
  // typing. Pristine drafts (draft === last saved) never schedule.
  // No setState here — dirtiness is derived at render from savedDraft.
  useEffect(() => {
    if (editingSection === null || draft === savedDraft) {
      return;
    }

    const seq = saveSeqRef.current + 1;
    saveSeqRef.current = seq;

    autosaveTimerRef.current = setTimeout(() => {
      autosaveTimerRef.current = null;

      if (seq !== saveSeqRef.current || isSavingRef.current) {
        return;
      }

      void flushAutosave();
    }, AUTOSAVE_DELAY_MS);

    return () => {
      if (autosaveTimerRef.current !== null) {
        clearTimeout(autosaveTimerRef.current);
        autosaveTimerRef.current = null;
      }
    };
  }, [draft, editingSection, savedDraft, flushAutosave]);

  useEffect(() => {
    if (editingSection === null) {
      setDraft(data);
    }
  }, [data, editingSection]);

  // Flush-then-switch: persist pending edits before moving to another
  // section. Stays put only when the flush itself failed, so no typed
  // content is ever silently discarded.
  async function startEditing(section: EditingSection) {
    if (
      editingSection !== null &&
      section !== editingSection &&
      draftRef.current !== lastSavedRef.current
    ) {
      const saved = await flushAutosave();

      if (!saved) {
        return;
      }
    }

    cancelPendingAutosave();
    setDraft(data);
    lastSavedRef.current = data;
    setSavedDraft(data);
    setAutosavedAt(null);
    setEditingSection(section);
  }

  function cancelEditing() {
    cancelPendingAutosave();
    setDraft(data);
    setSavedDraft(data);
    setAutosavedAt(null);
    setEditingSection(null);
  }

  async function saveEditing() {
    if (editingSection === null) {
      return;
    }

    cancelPendingAutosave();
    await onSave(draft);
    setEditingSection(null);
  }

  // Render-safe dirtiness: a new draft object means the user typed
  // since the last persisted save, so the stamp hides itself.
  const isAutosaveDirty = draft !== savedDraft;

  const autosaveStatusText =
    editingSection === null
      ? null
      : isSaving
        ? "Saving…"
        : saveFailed
          ? null
          : autosavedAt && !isAutosaveDirty
            ? `Saved ${autosavedAt}`
            : null;

  function updateListItem(
    section: keyof BRDData,
    field: string,
    value: string[],
  ) {
    setDraft((current) => {
      const sectionData = current[section];

      return {
        ...current,
        [section]: {
          ...sectionData,
          [field]: value,
        },
      } as BRDData;
    });
  }

  function updateStakeholder(
    index: number,
    field: "name" | "role" | "organization",
    value: string,
  ) {
    setDraft((current) => {
      const stakeholders = [...current.stakeholders.stakeholders];

      stakeholders[index] = {
        ...stakeholders[index],
        [field]: value,
      };

      return {
        ...current,
        stakeholders: {
          stakeholders,
        },
      };
    });
  }

  function addStakeholder() {
    setDraft((current) => ({
      ...current,
      stakeholders: {
        stakeholders: [
          ...current.stakeholders.stakeholders,
          {
            name: "",
            role: "",
            organization: "",
          },
        ],
      },
    }));
  }

  function removeStakeholder(index: number) {
    setDraft((current) => ({
      ...current,
      stakeholders: {
        stakeholders: current.stakeholders.stakeholders.filter(
          (_, stakeholderIndex) => stakeholderIndex !== index,
        ),
      },
    }));
  }

  return (
    <article
      className="mx-auto w-full print:max-w-none"
      onBlur={(event) => {
        // Focus left the document entirely (e.g. into the Q&A rail):
        // flush any pending autosave. Moves within the article
        // (Save/Cancel/another section's Edit) are handled by their
        // own paths.
        if (
          !event.currentTarget.contains(event.relatedTarget as Node | null)
        ) {
          void flushAutosave();
        }
      }}
    >
      <header className="px-2 py-8 sm:px-4">
        <h1 className="text-[32px] leading-[1.25] font-semibold tracking-[-0.5px] text-ink sm:text-[40px] sm:leading-[1.2] sm:tracking-[-1px]">
          {data.project_overview.project_name}
        </h1>

        <p className="mt-2 max-w-2xl text-lg leading-7 font-medium text-steel">
          {data.project_overview.description}
        </p>

        {(generatedOn || updatedOn || editedByUser) && (
          <p className="mt-4 text-sm leading-5 text-stone">
            {[generatedOn && `Generated ${generatedOn}`, updatedOn && updatedOn !== generatedOn && `Updated ${updatedOn}`, editedByUser && "Edited by you"]
              .filter(Boolean)
              .join(" · ")}
          </p>
        )}
      </header>

      <div className="overflow-hidden rounded-2xl border border-hairline bg-canvas shadow-level-2 print:border-0 print:rounded-none print:shadow-none">
        <div aria-hidden="true" className="h-1 bg-brand-coral print:hidden" />
        <div className="px-6 py-8 sm:px-10">
        {/* 01 — Executive Summary */}
        <Section
          number={1}
          title="Executive Summary"
          isEditing={editingSection === "executive_summary"}
          onEdit={() => startEditing("executive_summary")}
          onCancel={cancelEditing}
          onSave={saveEditing}
          isSaving={isSaving}
          saveFailed={saveFailed}
          autosaveText={autosaveStatusText}
        >
          {editingSection === "executive_summary" ? (
            <EditableField
              label="Summary"
              value={draft.executive_summary.content}
              onChange={(value) =>
                setDraft((current) => ({
                  ...current,
                  executive_summary: {
                    content: value,
                  },
                }))
              }
              multiline
            />
          ) : (
            <p className="text-justify text-base leading-6 whitespace-pre-line text-ink">
              {data.executive_summary.content}
            </p>
          )}
        </Section>

        {/* 02 — Project Overview */}
        <Section
          number={2}
          title="Project Overview"
          isEditing={editingSection === "project_overview"}
          onEdit={() => startEditing("project_overview")}
          onCancel={cancelEditing}
          onSave={saveEditing}
          isSaving={isSaving}
          saveFailed={saveFailed}
          autosaveText={autosaveStatusText}
        >
          {editingSection === "project_overview" ? (
            <div className="space-y-6">
              <EditableField
                label="Project Name"
                value={draft.project_overview.project_name}
                onChange={(value) =>
                  setDraft((current) => ({
                    ...current,
                    project_overview: {
                      ...current.project_overview,
                      project_name: value,
                    },
                  }))
                }
              />

              <EditableField
                label="Description"
                value={draft.project_overview.description}
                onChange={(value) =>
                  setDraft((current) => ({
                    ...current,
                    project_overview: {
                      ...current.project_overview,
                      description: value,
                    },
                  }))
                }
                multiline
              />
            </div>
          ) : (
            <div className="space-y-6">
              <div>
                <h3 className="text-sm font-medium text-ink">
                  Project Name
                </h3>

                <p className="mt-2 text-justify text-base leading-6 text-ink">
                  {data.project_overview.project_name}
                </p>
              </div>

              <div>
                <h3 className="text-sm font-medium text-ink">
                  Description
                </h3>

                <p className="mt-2 text-justify text-base leading-6 whitespace-pre-line text-ink">
                  {data.project_overview.description}
                </p>
              </div>
            </div>
          )}
        </Section>

        {/* 03 — Business Objectives */}
        <Section
          number={3}
          title="Business Objectives"
          isEditing={editingSection === "business_objectives"}
          onEdit={() => startEditing("business_objectives")}
          onCancel={cancelEditing}
          onSave={saveEditing}
          isSaving={isSaving}
          saveFailed={saveFailed}
          autosaveText={autosaveStatusText}
        >
          {editingSection === "business_objectives" ? (
            <EditableList
              items={draft.business_objectives.objectives}
              onChange={(items) =>
                updateListItem(
                  "business_objectives",
                  "objectives",
                  items,
                )
              }
              placeholder="Enter business objective"
            />
          ) : (
            <BulletList
              items={data.business_objectives.objectives}
            />
          )}
        </Section>

        {/* 04 — Scope */}
        <Section
          number={4}
          title="Scope"
          isEditing={editingSection === "scope"}
          onEdit={() => startEditing("scope")}
          onCancel={cancelEditing}
          onSave={saveEditing}
          isSaving={isSaving}
          saveFailed={saveFailed}
          autosaveText={autosaveStatusText}
        >
          {editingSection === "scope" ? (
            <div className="space-y-8">
              <div>
                <h3 className="mb-2 text-sm font-medium text-ink">
                  In Scope
                </h3>

                <EditableList
                  items={draft.scope.in_scope}
                  onChange={(items) =>
                    updateListItem(
                      "scope",
                      "in_scope",
                      items,
                    )
                  }
                  placeholder="Enter in-scope item"
                />
              </div>

              <div>
                <h3 className="mb-2 text-sm font-medium text-ink">
                  Out of Scope
                </h3>

                <EditableList
                  items={draft.scope.out_of_scope}
                  onChange={(items) =>
                    updateListItem(
                      "scope",
                      "out_of_scope",
                      items,
                    )
                  }
                  placeholder="Enter out-of-scope item"
                />
              </div>
            </div>
          ) : (
            <div className="space-y-8">
              <div>
                <h3 className="mb-2 text-sm font-medium text-ink">
                  In Scope
                </h3>

                <BulletList items={data.scope.in_scope} />
              </div>

              <div>
                <h3 className="mb-2 text-sm font-medium text-ink">
                  Out of Scope
                </h3>

                <BulletList items={data.scope.out_of_scope} />
              </div>
            </div>
          )}
        </Section>

        {/* 05 — Stakeholders */}
        <Section
          number={5}
          title="Stakeholders"
          isEditing={editingSection === "stakeholders"}
          onEdit={() => startEditing("stakeholders")}
          onCancel={cancelEditing}
          onSave={saveEditing}
          isSaving={isSaving}
          saveFailed={saveFailed}
          autosaveText={autosaveStatusText}
        >
          {editingSection === "stakeholders" ? (
            <div className="space-y-4">
              {draft.stakeholders.stakeholders.length === 0 && (
                <p className="text-sm text-steel italic">
                  No stakeholders added.
                </p>
              )}

              {draft.stakeholders.stakeholders.map(
                (stakeholder, index) => (
                  <div
                    key={index}
                    className="rounded-2xl border border-hairline bg-surface p-4"
                  >
                    <div className="grid gap-4 md:grid-cols-3">
                      <EditableField
                        label="Name"
                        value={stakeholder.name}
                        onChange={(value) =>
                          updateStakeholder(
                            index,
                            "name",
                            value,
                          )
                        }
                      />

                      <EditableField
                        label="Role"
                        value={stakeholder.role ?? ""}
                        onChange={(value) =>
                          updateStakeholder(
                            index,
                            "role",
                            value,
                          )
                        }
                      />

                      <EditableField
                        label="Organization"
                        value={stakeholder.organization ?? ""}
                        onChange={(value) =>
                          updateStakeholder(
                            index,
                            "organization",
                            value,
                          )
                        }
                      />
                    </div>

                    <div className="mt-4 flex justify-end">
                      <button
                        type="button"
                        onClick={() =>
                          removeStakeholder(index)
                        }
                        className="rounded-full border border-hairline px-4 py-2 text-[13px] font-medium text-steel transition-colors hover:bg-primary/5 hover:text-ink"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                ),
              )}

              <button
                type="button"
                onClick={addStakeholder}
                className="rounded-full border border-hairline px-5 py-2 text-[13px] font-medium text-ink transition-colors hover:bg-primary/5"
              >
                + Add stakeholder
              </button>
            </div>
          ) : data.stakeholders.stakeholders.length === 0 ? (
            <p className="text-[15px] text-steel italic">
              None specified.
            </p>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-hairline">
              <table className="w-full text-left text-sm leading-5">
                <thead className="bg-surface">
                  <tr>
                    <th className="px-4 py-3 text-sm font-medium text-ink">
                      Name
                    </th>

                    <th className="px-4 py-3 text-sm font-medium text-ink">
                      Role
                    </th>

                    <th className="px-4 py-3 text-sm font-medium text-ink">
                      Organization
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {data.stakeholders.stakeholders.map(
                    (stakeholder, index) => (
                      <tr
                        key={index}
                        className="border-b border-hairline-soft last:border-b-0"
                      >
                        <td className="px-4 py-3 align-top text-justify font-medium text-ink">
                          {stakeholder.name}
                        </td>

                        <td className="px-4 py-3 align-top text-justify text-steel">
                          {stakeholder.role || "—"}
                        </td>

                        <td className="px-4 py-3 align-top text-justify text-steel">
                          {stakeholder.organization || "—"}
                        </td>
                      </tr>
                    ),
                  )}
                </tbody>
              </table>
            </div>
          )}
        </Section>

        {/* 06 — Business Requirements */}
        <Section
          number={6}
          title="Business Requirements"
          isEditing={editingSection === "business_requirements"}
          onEdit={() => startEditing("business_requirements")}
          onCancel={cancelEditing}
          onSave={saveEditing}
          isSaving={isSaving}
          saveFailed={saveFailed}
          autosaveText={autosaveStatusText}
        >
          {editingSection === "business_requirements" ? (
            <EditableList
              items={draft.business_requirements.requirements}
              onChange={(items) =>
                updateListItem(
                  "business_requirements",
                  "requirements",
                  items,
                )
              }
              placeholder="Enter business requirement"
            />
          ) : (
            <BulletList
              items={data.business_requirements.requirements}
            />
          )}
        </Section>

        {/* 07 — Functional Requirements */}
        <Section
          number={7}
          title="Functional Requirements"
          isEditing={editingSection === "functional_requirements"}
          onEdit={() => startEditing("functional_requirements")}
          onCancel={cancelEditing}
          onSave={saveEditing}
          isSaving={isSaving}
          saveFailed={saveFailed}
          autosaveText={autosaveStatusText}
        >
          {editingSection === "functional_requirements" ? (
            <EditableList
              items={draft.functional_requirements.requirements}
              onChange={(items) =>
                updateListItem(
                  "functional_requirements",
                  "requirements",
                  items,
                )
              }
              placeholder="Enter functional requirement"
            />
          ) : (
            <BulletList
              items={data.functional_requirements.requirements}
            />
          )}
        </Section>

        {/* 08 — Non-Functional Requirements */}
        <Section
          number={8}
          title="Non-Functional Requirements"
          isEditing={
            editingSection === "non_functional_requirements"
          }
          onEdit={() =>
            startEditing("non_functional_requirements")
          }
          onCancel={cancelEditing}
          onSave={saveEditing}
          isSaving={isSaving}
          saveFailed={saveFailed}
          autosaveText={autosaveStatusText}
        >
          {editingSection === "non_functional_requirements" ? (
            <EditableList
              items={
                draft.non_functional_requirements.requirements
              }
              onChange={(items) =>
                updateListItem(
                  "non_functional_requirements",
                  "requirements",
                  items,
                )
              }
              placeholder="Enter non-functional requirement"
            />
          ) : (
            <BulletList
              items={
                data.non_functional_requirements.requirements
              }
            />
          )}
        </Section>

        {/* 09 — Assumptions & Constraints */}
        <Section
          number={9}
          title="Assumptions & Constraints"
          isEditing={
            editingSection === "assumptions_and_constraints"
          }
          onEdit={() =>
            startEditing("assumptions_and_constraints")
          }
          onCancel={cancelEditing}
          onSave={saveEditing}
          isSaving={isSaving}
          saveFailed={saveFailed}
          autosaveText={autosaveStatusText}
        >
          {editingSection === "assumptions_and_constraints" ? (
            <div className="space-y-8">
              <div>
                <h3 className="mb-2 text-sm font-medium text-ink">
                  Assumptions
                </h3>

                <EditableList
                  items={
                    draft.assumptions_and_constraints.assumptions
                  }
                  onChange={(items) =>
                    updateListItem(
                      "assumptions_and_constraints",
                      "assumptions",
                      items,
                    )
                  }
                  placeholder="Enter assumption"
                />
              </div>

              <div>
                <h3 className="mb-2 text-sm font-medium text-ink">
                  Constraints
                </h3>

                <EditableList
                  items={
                    draft.assumptions_and_constraints.constraints
                  }
                  onChange={(items) =>
                    updateListItem(
                      "assumptions_and_constraints",
                      "constraints",
                      items,
                    )
                  }
                  placeholder="Enter constraint"
                />
              </div>
            </div>
          ) : (
            <div className="space-y-8">
              <div>
                <h3 className="mb-2 text-sm font-medium text-ink">
                  Assumptions
                </h3>

                <BulletList
                  items={
                    data.assumptions_and_constraints.assumptions
                  }
                />
              </div>

              <div>
                <h3 className="mb-2 text-sm font-medium text-ink">
                  Constraints
                </h3>

                <BulletList
                  items={
                    data.assumptions_and_constraints.constraints
                  }
                />
              </div>
            </div>
          )}
        </Section>

        {/* 10 — Risks & Decisions */}
        <Section
          number={10}
          title="Risks & Decisions"
          isEditing={editingSection === "risks_and_decisions"}
          onEdit={() => startEditing("risks_and_decisions")}
          onCancel={cancelEditing}
          onSave={saveEditing}
          isSaving={isSaving}
          saveFailed={saveFailed}
          autosaveText={autosaveStatusText}
        >
          {editingSection === "risks_and_decisions" ? (
            <div className="space-y-8">
              <div>
                <h3 className="mb-2 text-sm font-medium text-ink">
                  Risks
                </h3>

                <EditableList
                  items={draft.risks_and_decisions.risks}
                  onChange={(items) =>
                    updateListItem(
                      "risks_and_decisions",
                      "risks",
                      items,
                    )
                  }
                  placeholder="Enter risk"
                />
              </div>

              <div>
                <h3 className="mb-2 text-sm font-medium text-ink">
                  Decisions
                </h3>

                <EditableList
                  items={draft.risks_and_decisions.decisions}
                  onChange={(items) =>
                    updateListItem(
                      "risks_and_decisions",
                      "decisions",
                      items,
                    )
                  }
                  placeholder="Enter decision"
                />
              </div>
            </div>
          ) : (
            <div className="space-y-8">
              <div>
                <h3 className="mb-2 text-sm font-medium text-ink">
                  Risks
                </h3>

                <BulletList
                  items={data.risks_and_decisions.risks}
                />
              </div>

              <div>
                <h3 className="mb-2 text-sm font-medium text-ink">
                  Decisions
                </h3>

                <BulletList
                  items={data.risks_and_decisions.decisions}
                />
              </div>
            </div>
          )}
        </Section>

        {/* 11 — Open Questions */}
        <Section
          number={11}
          title="Open Questions"
          isEditing={editingSection === "open_questions"}
          onEdit={() => startEditing("open_questions")}
          onCancel={cancelEditing}
          onSave={saveEditing}
          isSaving={isSaving}
          saveFailed={saveFailed}
          autosaveText={autosaveStatusText}
        >
          {editingSection === "open_questions" ? (
            <EditableList
              items={draft.open_questions.questions}
              onChange={(items) =>
                updateListItem(
                  "open_questions",
                  "questions",
                  items,
                )
              }
              placeholder="Enter open question"
            />
          ) : (
            <BulletList
              items={data.open_questions.questions}
            />
          )}
        </Section>
        </div>
      </div>
    </article>
  );
}
