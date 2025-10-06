"""
Preferences and current state management using SQLAlchemy.

Handles user preferences and current state (goals, blockers, next steps).
"""
from datetime import datetime
from typing import Dict, Optional
from uuid import UUID

from sqlalchemy import select, delete, update, func
from sqlalchemy.orm import Session

from ..models import Preference, CurrentState


class PreferencesStateManager:
    """Manages preferences and current state using SQLAlchemy."""

    def __init__(self, db_session: Session, project_id: Optional[UUID] = None):
        """
        Initialize preferences/state manager.

        Args:
            db_session: SQLAlchemy session
            project_id: Project ID for multi-tenant isolation (None for OSS mode)
        """
        self.session = db_session
        self.project_id = project_id

    # ========================================================================
    # Preferences
    # ========================================================================

    def add_preference(self, category: str, content: str) -> None:
        """Add a preference to a specific category."""
        pref = Preference(
            project_id=self.project_id,
            category=category,
            content=content
        )
        self.session.add(pref)
        self.session.commit()

    def get_preferences(self) -> Dict:
        """Get all preferences organized by category."""
        query = select(Preference)

        # Apply project filter
        if self.project_id:
            query = query.where(Preference.project_id == self.project_id)

        # Order by category, then timestamp descending
        query = query.order_by(Preference.category, Preference.timestamp.desc())

        prefs_list = self.session.execute(query).scalars().all()

        # Organize by category
        prefs = {}
        for pref in prefs_list:
            if pref.category not in prefs:
                prefs[pref.category] = []
            prefs[pref.category].append({
                'content': pref.content,
                'timestamp': pref.timestamp.isoformat()
            })

        return prefs

    # ========================================================================
    # Current State (Goals, Blockers, Next Steps)
    # ========================================================================

    def add_goal(self, goal: str) -> None:
        """Add a goal to current state."""
        state = CurrentState(
            project_id=self.project_id,
            type='goal',
            content=goal
        )
        self.session.add(state)
        self.session.commit()

    def add_next_step(self, step: str) -> None:
        """Add a next step to current state."""
        state = CurrentState(
            project_id=self.project_id,
            type='next_step',
            content=step
        )
        self.session.add(state)
        self.session.commit()

    def get_current_state(self) -> Dict:
        """Get current state (goals, blockers, next steps)."""
        state = {
            "goals": [],
            "blockers": [],
            "next_steps": []
        }

        # Get goals
        query = select(CurrentState).where(
            CurrentState.type == 'goal',
            CurrentState.completed == False
        )
        if self.project_id:
            query = query.where(CurrentState.project_id == self.project_id)
        query = query.order_by(CurrentState.timestamp.desc())

        goals = self.session.execute(query).scalars().all()
        state["goals"] = [
            {"content": g.content, "timestamp": g.timestamp.isoformat()}
            for g in goals
        ]

        # Get blockers
        query = select(CurrentState).where(
            CurrentState.type == 'blocker',
            CurrentState.completed == False
        )
        if self.project_id:
            query = query.where(CurrentState.project_id == self.project_id)
        query = query.order_by(CurrentState.timestamp.desc())

        blockers = self.session.execute(query).scalars().all()
        state["blockers"] = [
            {"content": b.content, "timestamp": b.timestamp.isoformat()}
            for b in blockers
        ]

        # Get next steps
        query = select(CurrentState).where(
            CurrentState.type == 'next_step',
            CurrentState.completed == False
        )
        if self.project_id:
            query = query.where(CurrentState.project_id == self.project_id)
        query = query.order_by(CurrentState.timestamp.desc())

        steps = self.session.execute(query).scalars().all()
        state["next_steps"] = [
            {"content": s.content, "timestamp": s.timestamp.isoformat()}
            for s in steps
        ]

        return state

    def clear_goals(self) -> None:
        """Clear all goals."""
        query = delete(CurrentState).where(CurrentState.type == 'goal')
        if self.project_id:
            query = query.where(CurrentState.project_id == self.project_id)

        self.session.execute(query)
        self.session.commit()

    def clear_next_steps(self) -> None:
        """Clear all next steps."""
        query = delete(CurrentState).where(CurrentState.type == 'next_step')
        if self.project_id:
            query = query.where(CurrentState.project_id == self.project_id)

        self.session.execute(query)
        self.session.commit()

    def complete_goal(self, goal_text: str) -> bool:
        """
        Mark a goal as completed by matching text.

        Args:
            goal_text: The goal text to match (case-insensitive, partial match)

        Returns:
            True if a goal was found and marked complete, False otherwise
        """
        # Find goal by partial text match
        query = select(CurrentState).where(
            CurrentState.type == 'goal',
            CurrentState.completed == False,
            func.lower(CurrentState.content).like(f"%{goal_text.lower()}%")
        )
        if self.project_id:
            query = query.where(CurrentState.project_id == self.project_id)

        query = query.order_by(CurrentState.timestamp.desc()).limit(1)

        goal = self.session.execute(query).scalar_one_or_none()

        if goal:
            goal.completed = True
            self.session.commit()
            return True
        return False

    def complete_next_step(self, step_text: str) -> bool:
        """
        Mark a next step as completed by matching text.

        Args:
            step_text: The step text to match (case-insensitive, partial match)

        Returns:
            True if a step was found and marked complete, False otherwise
        """
        # Find step by partial text match
        query = select(CurrentState).where(
            CurrentState.type == 'next_step',
            CurrentState.completed == False,
            func.lower(CurrentState.content).like(f"%{step_text.lower()}%")
        )
        if self.project_id:
            query = query.where(CurrentState.project_id == self.project_id)

        query = query.order_by(CurrentState.timestamp.desc()).limit(1)

        step = self.session.execute(query).scalar_one_or_none()

        if step:
            step.completed = True
            self.session.commit()
            return True
        return False

    def clear_completed_goals(self) -> int:
        """
        Remove completed goals from database.

        Returns:
            Number of goals removed
        """
        query = delete(CurrentState).where(
            CurrentState.type == 'goal',
            CurrentState.completed == True
        )
        if self.project_id:
            query = query.where(CurrentState.project_id == self.project_id)

        result = self.session.execute(query)
        self.session.commit()
        return result.rowcount

    def clear_completed_next_steps(self) -> int:
        """
        Remove completed next steps from database.

        Returns:
            Number of steps removed
        """
        query = delete(CurrentState).where(
            CurrentState.type == 'next_step',
            CurrentState.completed == True
        )
        if self.project_id:
            query = query.where(CurrentState.project_id == self.project_id)

        result = self.session.execute(query)
        self.session.commit()
        return result.rowcount
