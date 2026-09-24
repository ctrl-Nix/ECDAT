import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';

/**
 * @param {number} scanId
 * @param {{risk_tier?: string[], primitive?: string[], algorithm?: string[], language?: string[], sort_by?: 'risk_tier'|'algorithm'|'primitive'|'language'|'file'|'line', sort_dir?: 'asc'|'desc', limit?: number, offset?: number}} [params]
 */
export function useFindings(scanId, params = {}) {
  return useQuery({
    queryKey: ['findings', scanId, params],
    enabled: !!scanId,
    queryFn: async () => {
      const response = await api.get(`/scans/${scanId}/findings`, {
        params,
        paramsSerializer: {
          serialize: (query) => {
            const search = new URLSearchParams();
            Object.entries(query).forEach(([key, value]) => {
              if (Array.isArray(value)) value.forEach((item) => search.append(key, item));
              else if (value !== undefined && value !== null) search.append(key, value);
            });
            return search.toString();
          },
        },
      });
      return response.data;
    },
    retry: 1,
  });
}
