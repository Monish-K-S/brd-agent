import { useEffect, useState } from "react";

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

type BRDViewerProps = {
  data: BRDData;
  onSave: (data: BRDData) => Promise<void>;
  isSaving: boolean;
};

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

function Section({
  number,
  title,
  isEditing,
  onEdit,
  onCancel,
  onSave,
  isSaving,
  children,
}: {
  number: number;
  title: string;
  isEditing: boolean;
  onEdit: () => void;
  onCancel: () => void;
  onSave: () => void;
  isSaving: boolean;
  children: React.ReactNode;
}) {
  return (
    <section className="border-t border-black/8 py-8 first:border-t-0 first:pt-0">
      <div className="mb-5 flex items-center justify-between gap-4">
        <div className="flex items-baseline gap-3">
          <span className="font-mono text-[11px] font-medium tracking-[0.55px] text-[#999999]">
            {String(number).padStart(2, "0")}
          </span>

          <h2 className="text-[22px] leading-[25.3px] font-medium tracking-[-0.22px] text-black">
            {title}
          </h2>
        </div>

        {!isEditing && (
          <button
            type="button"
            onClick={onEdit}
            className="rounded-[4px] border border-black/8 px-4 py-2 font-mono text-[16px] leading-4 font-medium tracking-[0.08px] text-black uppercase transition-colors print:hidden hover:bg-black/5"
          >
            Edit
          </button>
        )}
      </div>

      {children}

      {isEditing && (
        <div className="mt-6 flex items-center justify-end gap-3 border-t border-black/8 pt-5 print:hidden">
          <button
            type="button"
            onClick={onCancel}
            disabled={isSaving}
            className="rounded-[4px] border border-black/8 px-4 py-2 font-mono text-[16px] leading-4 font-medium tracking-[0.08px] text-black uppercase transition-colors hover:bg-black/5 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Cancel
          </button>

          <button
            type="button"
            onClick={onSave}
            disabled={isSaving}
            className="rounded-[4px] bg-black px-5 py-2 font-mono text-[16px] leading-4 font-medium tracking-[0.08px] text-white uppercase transition-colors hover:opacity-80 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isSaving ? "Saving..." : "Save"}
          </button>
        </div>
      )}
    </section>
  );
}

function BulletList({ items }: { items: string[] }) {
  if (items.length === 0) {
    return (
      <p className="text-sm text-[#999999] italic">
        None specified.
      </p>
    );
  }

  return (
    <ul className="space-y-3 pl-5 text-base leading-6 text-black">
      {items.map((item, index) => (
        <li key={index} className="list-disc pl-1">
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
            className="min-h-[72px] flex-1 resize-y rounded-[4px] border border-black/8 bg-white px-4 py-3 text-sm leading-6 text-black outline-none transition-colors placeholder:text-[#999999] focus:border-black"
          />

          <button
            type="button"
            onClick={() => removeItem(index)}
            className="rounded-[4px] border border-black/8 px-3 py-2 font-mono text-[11px] font-medium tracking-[0.055px] text-[#999999] uppercase transition-colors hover:bg-black/5 hover:text-black"
          >
            Remove
          </button>
        </div>
      ))}

      <button
        type="button"
        onClick={addItem}
        className="rounded-[4px] border border-black/8 px-4 py-2 font-mono text-[16px] leading-4 font-medium tracking-[0.08px] text-black uppercase transition-colors hover:bg-black/5"
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
      <label className="font-mono text-[11px] leading-[15.4px] font-medium tracking-[0.055px] text-black uppercase">
        {label}
      </label>

      {multiline ? (
        <textarea
          value={value}
          onChange={(event) => onChange(event.target.value)}
          rows={5}
          className="mt-2 w-full resize-y rounded-[4px] border border-black/8 bg-white px-4 py-3 text-sm leading-6 text-black outline-none transition-colors placeholder:text-[#999999] focus:border-black"
        />
      ) : (
        <input
          type="text"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="mt-2 w-full rounded-[4px] border border-black/8 bg-white px-4 py-3 text-sm leading-6 text-black outline-none transition-colors placeholder:text-[#999999] focus:border-black"
        />
      )}
    </div>
  );
}

export function BRDViewer({
  data,
  onSave,
  isSaving,
}: BRDViewerProps) {
  const [draft, setDraft] = useState<BRDData>(data);

  const [editingSection, setEditingSection] =
    useState<EditingSection>(null);

  useEffect(() => {
    if (editingSection === null) {
      setDraft(data);
    }
  }, [data, editingSection]);

  function startEditing(section: EditingSection) {
    setDraft(data);
    setEditingSection(section);
  }

  function cancelEditing() {
    setDraft(data);
    setEditingSection(null);
  }

  async function saveEditing() {
    if (editingSection === null) {
      return;
    }

    await onSave(draft);
    setEditingSection(null);
  }

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
    <article className="mx-auto w-full max-w-4xl rounded-[4px] border border-black/8 bg-white print:max-w-none print:rounded-none print:border-0 print:shadow-none">
      {/* Document Header */}
      <header className="rounded-t-[4px] border-b border-black/8 bg-white px-6 py-12 sm:px-12 sm:py-20">
        <p className="font-mono text-[11px] leading-[11px] font-medium tracking-[0.55px] text-[#999999] uppercase">
          Business Requirements Document
        </p>

        <h1 className="mt-4 text-[40px] leading-[48px] font-medium tracking-[-0.8px] text-black">
          {data.project_overview.project_name}
        </h1>

        <p className="mt-4 max-w-2xl text-[18px] leading-[23.4px] font-normal tracking-[-0.18px] text-[#999999]">
          {data.project_overview.description}
        </p>
      </header>

      {/* Document Content */}
      <div className="px-6 py-8 sm:px-12 sm:py-10">
        {/* 01 — Executive Summary */}
        <Section
          number={1}
          title="Executive Summary"
          isEditing={editingSection === "executive_summary"}
          onEdit={() => startEditing("executive_summary")}
          onCancel={cancelEditing}
          onSave={saveEditing}
          isSaving={isSaving}
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
            <p className="text-base leading-6 whitespace-pre-line text-black">
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
                <h3 className="font-mono text-[11px] font-medium tracking-[0.55px] text-[#999999] uppercase">
                  Project Name
                </h3>

                <p className="mt-2 text-base leading-6 text-black">
                  {data.project_overview.project_name}
                </p>
              </div>

              <div>
                <h3 className="font-mono text-[11px] font-medium tracking-[0.55px] text-[#999999] uppercase">
                  Description
                </h3>

                <p className="mt-2 text-base leading-6 whitespace-pre-line text-black">
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
        >
          {editingSection === "scope" ? (
            <div className="space-y-8">
              <div>
                <h3 className="mb-3 font-mono text-[11px] font-medium tracking-[0.55px] text-[#999999] uppercase">
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
                <h3 className="mb-3 font-mono text-[11px] font-medium tracking-[0.55px] text-[#999999] uppercase">
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
                <h3 className="mb-3 font-mono text-[11px] font-medium tracking-[0.55px] text-[#999999] uppercase">
                  In Scope
                </h3>

                <BulletList items={data.scope.in_scope} />
              </div>

              <div>
                <h3 className="mb-3 font-mono text-[11px] font-medium tracking-[0.55px] text-[#999999] uppercase">
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
        >
          {editingSection === "stakeholders" ? (
            <div className="space-y-4">
              {draft.stakeholders.stakeholders.length === 0 && (
                <p className="text-sm text-[#999999] italic">
                  No stakeholders added.
                </p>
              )}

              {draft.stakeholders.stakeholders.map(
                (stakeholder, index) => (
                  <div
                    key={index}
                    className="rounded-[4px] border border-black/8 p-4"
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
                        className="rounded-[4px] border border-black/8 px-3 py-2 font-mono text-[11px] font-medium tracking-[0.055px] text-[#999999] uppercase transition-colors hover:bg-black/5 hover:text-black"
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
                className="rounded-[4px] border border-black/8 px-4 py-2 font-mono text-[16px] leading-4 font-medium tracking-[0.08px] text-black uppercase transition-colors hover:bg-black/5"
              >
                + Add stakeholder
              </button>
            </div>
          ) : data.stakeholders.stakeholders.length === 0 ? (
            <p className="text-sm text-[#999999] italic">
              None specified.
            </p>
          ) : (
            <div className="overflow-x-auto rounded-[4px] border border-black/8">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-black/8">
                  <tr>
                    <th className="px-4 py-3 font-mono text-[11px] font-medium tracking-[0.55px] text-[#999999] uppercase">
                      Name
                    </th>

                    <th className="px-4 py-3 font-mono text-[11px] font-medium tracking-[0.55px] text-[#999999] uppercase">
                      Role
                    </th>

                    <th className="px-4 py-3 font-mono text-[11px] font-medium tracking-[0.55px] text-[#999999] uppercase">
                      Organization
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {data.stakeholders.stakeholders.map(
                    (stakeholder, index) => (
                      <tr
                        key={index}
                        className="border-b border-black/8 last:border-b-0"
                      >
                        <td className="px-4 py-3 align-top font-medium text-black">
                          {stakeholder.name}
                        </td>

                        <td className="px-4 py-3 align-top text-[#999999]">
                          {stakeholder.role || "—"}
                        </td>

                        <td className="px-4 py-3 align-top text-[#999999]">
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
        >
          {editingSection === "assumptions_and_constraints" ? (
            <div className="space-y-8">
              <div>
                <h3 className="mb-3 font-mono text-[11px] font-medium tracking-[0.55px] text-[#999999] uppercase">
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
                <h3 className="mb-3 font-mono text-[11px] font-medium tracking-[0.55px] text-[#999999] uppercase">
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
                <h3 className="mb-3 font-mono text-[11px] font-medium tracking-[0.55px] text-[#999999] uppercase">
                  Assumptions
                </h3>

                <BulletList
                  items={
                    data.assumptions_and_constraints.assumptions
                  }
                />
              </div>

              <div>
                <h3 className="mb-3 font-mono text-[11px] font-medium tracking-[0.55px] text-[#999999] uppercase">
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
        >
          {editingSection === "risks_and_decisions" ? (
            <div className="space-y-8">
              <div>
                <h3 className="mb-3 font-mono text-[11px] font-medium tracking-[0.55px] text-[#999999] uppercase">
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
                <h3 className="mb-3 font-mono text-[11px] font-medium tracking-[0.55px] text-[#999999] uppercase">
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
                <h3 className="mb-3 font-mono text-[11px] font-medium tracking-[0.55px] text-[#999999] uppercase">
                  Risks
                </h3>

                <BulletList
                  items={data.risks_and_decisions.risks}
                />
              </div>

              <div>
                <h3 className="mb-3 font-mono text-[11px] font-medium tracking-[0.55px] text-[#999999] uppercase">
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
    </article>
  );
}
