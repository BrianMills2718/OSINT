"""
Human-in-the-Loop (HITL)

Allows users to review and approve research plans before execution.

Key Features:
- CLI-based approval flow (y/n/edit)
- Cost and time estimates displayed
- Plan visualization
- Feedback collection for plan revision

Phase 1: CLI only
Phase 2: Streamlit UI (future work)
"""

import logging
from typing import Dict
from schemas.research_brief import ResearchBrief, PlanApproval


class HumanInTheLoop:
    """
    Get user approval for research plans before execution.

    Phase 1: CLI-based approval (blocking input)
    Phase 2: Streamlit non-blocking UI (future work)
    """

    def __init__(self, mode: str = "cli", enabled: bool = True):
        """
        Initialize HITL.

        Args:
            mode: Interface mode ("cli" or "streamlit")
            enabled: Whether to require approval (False = auto-approve)
        """
        self.mode = mode
        self.enabled = enabled

        logging.info(f"HumanInTheLoop initialized: mode={mode}, enabled={enabled}")

    async def get_approval(self, brief: ResearchBrief) -> PlanApproval:
        """
        Get user approval for research plan.

        Args:
            brief: Research brief to approve

        Returns:
            PlanApproval with approval status and optional feedback

        Example:
            approval = await hitl.get_approval(brief)
            if approval.approved:
                # Execute plan
            else:
                # Abort or revise plan
        """
        if not self.enabled:
            logging.info("HITL disabled, auto-approving plan")
            return PlanApproval(approved=True, feedback=None)

        if self.mode == "cli":
            return await self._cli_approval(brief)
        elif self.mode == "streamlit":
            raise NotImplementedError(
                "Streamlit HITL pending Phase 2. "
                "Use mode='cli' or set enabled=False for now."
            )
        else:
            raise ValueError(f"Unknown HITL mode: {self.mode}")

    async def _cli_approval(self, brief: ResearchBrief) -> PlanApproval:
        """
        CLI-based approval flow.

        Displays plan, prompts for y/n/edit, collects feedback.

        Args:
            brief: Research brief

        Returns:
            PlanApproval
        """
        # Display plan
        self._display_plan(brief)

        # Get user input
        while True:
            try:
                response = input("\nApprove plan? [y/n/edit]: ").strip().lower()

                if response == "y" or response == "yes":
                    logging.info("User approved research plan")
                    return PlanApproval(approved=True, feedback=None)

                elif response == "n" or response == "no":
                    logging.info("User rejected research plan")
                    return PlanApproval(approved=False, feedback="User rejected plan")

                elif response == "edit":
                    feedback = input("Provide feedback (what to change): ").strip()

                    if feedback:
                        logging.info(f"User provided feedback: {feedback[:60]}...")
                        return PlanApproval(approved=False, feedback=feedback)
                    else:
                        print("No feedback provided. Please enter 'y', 'n', or 'edit' again.")
                        continue

                else:
                    print("Invalid input. Please enter 'y', 'n', or 'edit'.")
                    continue

            except (EOFError, KeyboardInterrupt):
                logging.info("User interrupted approval (Ctrl+C/Ctrl+D)")
                print("\n\nPlan approval cancelled.")
                return PlanApproval(approved=False, feedback="User cancelled")

    def _display_plan(self, brief: ResearchBrief):
        """
        Display research plan to user.

        Args:
            brief: Research brief to display
        """
        print("\n" + "=" * 80)
        print("RESEARCH PLAN")
        print("=" * 80)

        print(f"Objective: {brief.objective}")

        print(f"\nSub-questions ({len(brief.sub_questions)}):")
        for i, sq in enumerate(brief.sub_questions, 1):
            print(f"  {i}. {sq.question}")
            print(f"     Rationale: {sq.rationale}")
            print(f"     Sources: {', '.join(sq.suggested_categories)}")

        # Display estimates if available
        if brief.estimated_cost is not None:
            print(f"\nEstimated cost: ${brief.estimated_cost:.2f}")

        if brief.estimated_time is not None:
            minutes = brief.estimated_time // 60
            seconds = brief.estimated_time % 60
            if minutes > 0:
                print(f"Estimated time: {minutes}m {seconds}s")
            else:
                print(f"Estimated time: {seconds}s")

        # Display constraints if any
        if brief.constraints:
            print(f"\nConstraints:")
            for key, value in brief.constraints.items():
                print(f"  - {key}: {value}")

        print("=" * 80)
