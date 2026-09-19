import { Fragment } from "react";
import { STAGES, type StageStatus } from "../types";

export function Pipeline({ activeIndex }: { activeIndex: number }) {
  return (
    <section className="card pipeline fade-in" aria-live="polite">
      <h2>Verifying claim</h2>
      {STAGES.map((stage, index) => {
        const status: StageStatus =
          index < activeIndex ? "complete" : index === activeIndex ? "active" : "pending";
        return (
          <Fragment key={stage}>
            {index > 0 && <div className="stage-rail" />}
            <div className="stage" data-status={status}>
              <span className="stage-dot" />
              <span>{stage}</span>
            </div>
          </Fragment>
        );
      })}
    </section>
  );
}
