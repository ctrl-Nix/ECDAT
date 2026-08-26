import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';

export function useFindings(scanId, params = {}) {
  return useQuery({
    queryKey: ['findings', scanId, params],
    enabled: !!scanId,
    queryFn: async () => {
      const response = await api.get(`/scans/${scanId}/findings`, { params });
      return response.data;
    },
    retry: 1,
  });
}
