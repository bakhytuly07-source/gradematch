import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { MockService } from './mock';
import { ApiService } from './api';
import { createSessionService } from './session';
import type { User } from './types';
export * from './types';
export { validateImageFile } from './validation';
const apiUrl = import.meta.env['VITE_API_URL'];
const session = createSessionService(apiUrl ? new ApiService(apiUrl) : new MockService());
export const service = session.service;
export function useMe() {
  const [me, setMe] = useState<User | null | undefined>(undefined);
  useEffect(() => {
    let live = true;
    const unsubscribe = session.subscribe(u => {if (live) setMe(u);});
    service.getMe().catch((e: Error) => {if (live) {setMe(null); toast.error(e.message);}});
    return () => {live = false; unsubscribe();};
  }, []);
  return me;
}
