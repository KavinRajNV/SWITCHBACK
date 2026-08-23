import React, { createContext, useContext, useState, useEffect } from 'react';
import type { LearnerProfile, GoalProfile, TargetOccupation, PathResponse } from '../lib/api';

export interface MilestoneLog {
  skill: string;
  completed_at: string;
  evidence_type: string;
}

interface AppState {
  sessionId: string | null;
  learnerProfile: LearnerProfile | null;
  goalProfile: GoalProfile | null;
  targetOccupation: TargetOccupation | null;
  pathData: PathResponse | null;
  completedSkills: string[];
  completedLogs: MilestoneLog[];
  setSessionId: (id: string) => void;
  setLearnerProfile: (profile: LearnerProfile) => void;
  setGoalProfile: (profile: GoalProfile) => void;
  setTargetOccupation: (occ: TargetOccupation) => void;
  setPathData: (path: PathResponse) => void;
  addCompletedSkill: (skill: string, evidence_type?: string) => void;
  resetSession: () => void;
}

const AppContext = createContext<AppState | undefined>(undefined);

const LOCAL_STORAGE_KEY = 'switchback_app_session_v1';

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [sessionId, setSessionIdState] = useState<string | null>(() => {
    const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (saved) {
      try { return JSON.parse(saved).sessionId || null; } catch (e) { return null; }
    }
    return null;
  });

  const [learnerProfile, setLearnerProfileState] = useState<LearnerProfile | null>(() => {
    const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (saved) {
      try { return JSON.parse(saved).learnerProfile || null; } catch (e) { return null; }
    }
    return null;
  });

  const [goalProfile, setGoalProfileState] = useState<GoalProfile | null>(() => {
    const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (saved) {
      try { return JSON.parse(saved).goalProfile || null; } catch (e) { return null; }
    }
    return null;
  });

  const [targetOccupation, setTargetOccupationState] = useState<TargetOccupation | null>(() => {
    const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (saved) {
      try { return JSON.parse(saved).targetOccupation || null; } catch (e) { return null; }
    }
    return null;
  });

  const [pathData, setPathDataState] = useState<PathResponse | null>(() => {
    const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (saved) {
      try { return JSON.parse(saved).pathData || null; } catch (e) { return null; }
    }
    return null;
  });

  const [completedSkills, setCompletedSkillsState] = useState<string[]>(() => {
    const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (saved) {
      try { return JSON.parse(saved).completedSkills || []; } catch (e) { return []; }
    }
    return [];
  });

  const [completedLogs, setCompletedLogsState] = useState<MilestoneLog[]>(() => {
    const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (saved) {
      try { return JSON.parse(saved).completedLogs || []; } catch (e) { return []; }
    }
    return [];
  });

  useEffect(() => {
    const stateToSave = {
      sessionId,
      learnerProfile,
      goalProfile,
      targetOccupation,
      pathData,
      completedSkills,
      completedLogs,
    };
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(stateToSave));
  }, [sessionId, learnerProfile, goalProfile, targetOccupation, pathData, completedSkills, completedLogs]);

  const setSessionId = (id: string) => setSessionIdState(id);
  const setLearnerProfile = (profile: LearnerProfile) => setLearnerProfileState(profile);
  const setGoalProfile = (profile: GoalProfile) => setGoalProfileState(profile);
  const setTargetOccupation = (occ: TargetOccupation) => setTargetOccupationState(occ);
  const setPathData = (path: PathResponse) => setPathDataState(path);

  const addCompletedSkill = (skill: string, evidence_type = 'project_log') => {
    setCompletedSkillsState((prev) => (prev.includes(skill) ? prev : [...prev, skill]));
    setCompletedLogsState((prev) => {
      if (prev.some((l) => l.skill === skill)) return prev;
      return [...prev, { skill, completed_at: new Date().toISOString(), evidence_type }];
    });
  };

  const resetSession = () => {
    setSessionIdState(null);
    setLearnerProfileState(null);
    setGoalProfileState(null);
    setTargetOccupationState(null);
    setPathDataState(null);
    setCompletedSkillsState([]);
    setCompletedLogsState([]);
    localStorage.removeItem(LOCAL_STORAGE_KEY);
  };

  return (
    <AppContext.Provider
      value={{
        sessionId,
        learnerProfile,
        goalProfile,
        targetOccupation,
        pathData,
        completedSkills,
        completedLogs,
        setSessionId,
        setLearnerProfile,
        setGoalProfile,
        setTargetOccupation,
        setPathData,
        addCompletedSkill,
        resetSession,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};
