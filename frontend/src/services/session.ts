import { ServiceError, type GradeMatchService, type User } from './types';

/** Owns auth notifications and ignores responses from superseded sessions. */
export function createSessionService(base: GradeMatchService) {
  let generation = 0;
  let current: User | null = null;
  const listeners = new Set<(user: User | null) => void>();
  const emit = (user: User | null) => { current = user; listeners.forEach(l => l(user)); };
  const guarded = async <T>(run: () => Promise<T>): Promise<T> => {
    const g = generation;
    try { return await run(); }
    catch (error) {
      if (g === generation && error instanceof ServiceError && error.code === 'auth') { generation++; emit(null); }
      throw error;
    }
  };
  const service: GradeMatchService = {
    register: async (email, password) => { const g = ++generation; const user = await base.register(email, password); if (g === generation) emit(user); return user; },
    login: async (email, password) => { const g = ++generation; const user = await base.login(email, password); if (g === generation) emit(user); return user; },
    logout: async () => { const g = ++generation; emit(null); try { await base.logout(); } finally { if (g === generation) emit(null); } },
    getMe: async () => { const g = generation; const user = await base.getMe(); if (g === generation) emit(user); return g === generation ? user : current; },
    generateLook: f => base.generateLook(f),
    renderLut: (s, a) => base.renderLut(s, a),
    downloadLutCube: (s, a) => base.downloadLutCube(s, a),
    saveLook: input => guarded(() => base.saveLook(input)),
    listLooks: () => guarded(() => base.listLooks()),
    getLook: id => guarded(() => base.getLook(id)),
    renameLook: (id, name) => guarded(() => base.renameLook(id, name)),
    toggleFavorite: id => guarded(() => base.toggleFavorite(id)),
    deleteLook: id => guarded(() => base.deleteLook(id)),
  };
  return {service, subscribe(listener: (user: User | null) => void) { listeners.add(listener); return () => {listeners.delete(listener);}; }};
}
