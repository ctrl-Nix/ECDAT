import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';

export function useScans(params = {}) {
  return useQuery({
    queryKey: ['scans', params],
    queryFn: async () => {
      const response = await api.get('/scans', { params });
      return response.data;
    },
    retry: 1,
  });
}
