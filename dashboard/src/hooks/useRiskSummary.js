import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';

export function useRiskSummary(scanId) {
  return useQuery({
    queryKey: ['risk-summary', scanId],
    enabled: !!scanId,
    queryFn: async () => {
      const response = await api.get(`/scans/${scanId}/risk-summary`);
      return response.data;
    },
    retry: 1,
  });
}
