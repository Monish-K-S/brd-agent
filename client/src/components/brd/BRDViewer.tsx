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
};

function Section({
  number,
  title,
  children,
}: {
  number: number;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border-t py-8 first:border-t-0 first:pt-0">
      <div className="mb-5 flex items-baseline gap-3">
        <span className="text-sm font-medium text-muted-foreground">
          {String(number).padStart(2, "0")}
        </span>

        <h2 className="text-xl font-semibold tracking-tight">{title}</h2>
      </div>

      {children}
    </section>
  );
}

function BulletList({ items }: { items: string[] }) {
  if (items.length === 0) {
    return (
      <p className="text-sm italic text-muted-foreground">None specified.</p>
    );
  }

  return (
    <ul className="space-y-3 pl-5 text-sm leading-7">
      {items.map((item, index) => (
        <li key={index} className="list-disc pl-1">
          {item}
        </li>
      ))}
    </ul>
  );
}

export function BRDViewer({ data }: BRDViewerProps) {
  return (
    <article className="mx-auto w-full max-w-4xl bg-background shadow-sm">
      {/* Document Header */}
      <header className="border-b px-8 py-10 sm:px-12 sm:py-14">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
          Business Requirements Document
        </p>

        <h1 className="mt-4 text-3xl font-bold tracking-tight sm:text-4xl">
          {data.project_overview.project_name}
        </h1>

        <p className="mt-4 max-w-2xl text-sm leading-6 text-muted-foreground">
          {data.project_overview.description}
        </p>
      </header>

      {/* Document Content */}
      <div className="px-8 py-8 sm:px-12 sm:py-10">
        <Section number={1} title="Executive Summary">
          <p className="whitespace-pre-line text-sm leading-7">
            {data.executive_summary.content}
          </p>
        </Section>

        <Section number={2} title="Project Overview">
          <div className="space-y-6">
            <div>
              <h3 className="text-sm font-semibold">Project Name</h3>

              <p className="mt-2 text-sm leading-7">
                {data.project_overview.project_name}
              </p>
            </div>

            <div>
              <h3 className="text-sm font-semibold">Description</h3>

              <p className="mt-2 whitespace-pre-line text-sm leading-7">
                {data.project_overview.description}
              </p>
            </div>
          </div>
        </Section>

        <Section number={3} title="Business Objectives">
          <BulletList items={data.business_objectives.objectives} />
        </Section>

        <Section number={4} title="Scope">
          <div className="space-y-8">
            <div>
              <h3 className="mb-4 text-sm font-semibold">In Scope</h3>

              <BulletList items={data.scope.in_scope} />
            </div>

            <div>
              <h3 className="mb-4 text-sm font-semibold">Out of Scope</h3>

              <BulletList items={data.scope.out_of_scope} />
            </div>
          </div>
        </Section>

        <Section number={5} title="Stakeholders">
          {data.stakeholders.stakeholders.length === 0 ? (
            <p className="text-sm italic text-muted-foreground">
              None specified.
            </p>
          ) : (
            <div className="overflow-x-auto rounded-md border">
              <table className="w-full text-left text-sm">
                <thead className="border-b bg-muted/40">
                  <tr>
                    <th className="px-4 py-3 font-semibold">Name</th>

                    <th className="px-4 py-3 font-semibold">Role</th>

                    <th className="px-4 py-3 font-semibold">Organization</th>
                  </tr>
                </thead>

                <tbody>
                  {data.stakeholders.stakeholders.map((stakeholder, index) => (
                    <tr key={index} className="border-b last:border-b-0">
                      <td className="px-4 py-3 align-top font-medium">
                        {stakeholder.name}
                      </td>

                      <td className="px-4 py-3 align-top text-muted-foreground">
                        {stakeholder.role || "—"}
                      </td>

                      <td className="px-4 py-3 align-top text-muted-foreground">
                        {stakeholder.organization || "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Section>

        <Section number={6} title="Business Requirements">
          <BulletList items={data.business_requirements.requirements} />
        </Section>

        <Section number={7} title="Functional Requirements">
          <BulletList items={data.functional_requirements.requirements} />
        </Section>

        <Section number={8} title="Non-Functional Requirements">
          <BulletList items={data.non_functional_requirements.requirements} />
        </Section>

        <Section number={9} title="Assumptions & Constraints">
          <div className="space-y-8">
            <div>
              <h3 className="mb-4 text-sm font-semibold">Assumptions</h3>

              <BulletList
                items={data.assumptions_and_constraints.assumptions}
              />
            </div>

            <div>
              <h3 className="mb-4 text-sm font-semibold">Constraints</h3>

              <BulletList
                items={data.assumptions_and_constraints.constraints}
              />
            </div>
          </div>
        </Section>

        <Section number={10} title="Risks & Decisions">
          <div className="space-y-8">
            <div>
              <h3 className="mb-4 text-sm font-semibold">Risks</h3>

              <BulletList items={data.risks_and_decisions.risks} />
            </div>

            <div>
              <h3 className="mb-4 text-sm font-semibold">Decisions</h3>

              <BulletList items={data.risks_and_decisions.decisions} />
            </div>
          </div>
        </Section>

        <Section number={11} title="Open Questions">
          <BulletList items={data.open_questions.questions} />
        </Section>
      </div>
    </article>
  );
}
