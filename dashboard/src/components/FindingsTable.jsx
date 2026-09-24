import { useMemo, useState } from 'react';
import { ArrowDown, ArrowUp, ArrowUpDown, Search } from 'lucide-react';
import { findingColumns, riskTierOptions } from '../lib/constants.js';
import { useFindings } from '../hooks/useFindings.js';

/**
 * @param {{scanId: number, embedded?: boolean}} props
 */
export default function FindingsTable({ scanId, embedded = false }) {
  const [riskTiers, setRiskTiers] = useState([]);
  const [search, setSearch] = useState('');
  const [primitive, setPrimitive] = useState('');
  const [algorithm, setAlgorithm] = useState('');
  const [language, setLanguage] = useState('');
  const [sort, setSort] = useState({ sort_by: null, sort_dir: 'asc' });
  const query = useFindings(scanId, {
    ...(riskTiers.length ? { risk_tier: riskTiers } : {}),
    ...(sort.sort_by ? sort : {}),
  });

  const rows = useMemo(() => {
    const findings = query.data?.findings ?? [];
    const includes = (value, term) => !term || String(value ?? '').toLowerCase().includes(term.toLowerCase());
    return findings.filter((finding) => (
      (!search || includes(finding.file, search) || includes(finding.algorithm, search))
      && includes(finding.algorithm, algorithm)
      && includes(finding.primitive, primitive)
      && includes(finding.language, language)
    ));
  }, [query.data, search, primitive, algorithm, language]);

  const toggleSort = (column) => {
    setSort((current) => ({
      sort_by: column,
      sort_dir: current.sort_by === column && current.sort_dir === 'asc' ? 'desc' : 'asc',
    }));
  };

  return (
    <section className={embedded ? 'space-y-4' : 'card space-y-4 p-5'}>
      {!embedded && <h2 className="text-lg font-semibold" style={{ color: 'var(--t1)' }}>Findings</h2>}

      <div className="flex flex-wrap items-end gap-3">
        <label className="flex min-w-52 flex-col gap-1 text-xs" style={{ color: 'var(--t2)' }}>
          Search file or algorithm
          <span className="flex items-center gap-2 rounded-xl border px-3 py-2" style={{ borderColor: 'var(--border)', background: 'var(--surface-h)' }}>
            <Search className="h-4 w-4 shrink-0" style={{ color: 'var(--t3)' }} />
            <input aria-label="Search file or algorithm" value={search} onChange={(event) => setSearch(event.target.value)} className="w-full bg-transparent text-sm focus:outline-none" style={{ color: 'var(--t1)' }} />
          </span>
        </label>
        <label className="flex min-w-44 flex-col gap-1 text-xs" style={{ color: 'var(--t2)' }}>
          Risk tier
          <select aria-label="Risk tier" multiple value={riskTiers} onChange={(event) => setRiskTiers(Array.from(event.target.selectedOptions, (option) => option.value))} className="field min-h-20">
            {riskTierOptions.map((tier) => <option key={tier} value={tier}>{tier}</option>)}
          </select>
        </label>
        {[
          ['Primitive', primitive, setPrimitive],
          ['Algorithm', algorithm, setAlgorithm],
          ['Language', language, setLanguage],
        ].map(([label, value, setter]) => (
          <label key={label} className="flex min-w-36 flex-col gap-1 text-xs" style={{ color: 'var(--t2)' }}>
            {label}
            <input aria-label={label} value={value} onChange={(event) => setter(event.target.value)} className="field" />
          </label>
        ))}
      </div>

      {query.isLoading ? (
        <div className="card p-6 text-center text-sm" style={{ color: 'var(--t2)' }}>Loading findings…</div>
      ) : query.isError ? (
        <div role="alert" className="card p-6 text-sm" style={{ color: 'var(--critical)' }}>
          Could not load findings: {query.error?.response?.data?.detail || query.error?.message || 'request failed'}
        </div>
      ) : (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead><tr>{findingColumns.map((column) => (
                <th key={column.key}>
                  {column.sortable ? (
                    <button type="button" onClick={() => toggleSort(column.key)} className="inline-flex items-center gap-1">
                      {column.header}
                      {sort.sort_by === column.key
                        ? (sort.sort_dir === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)
                        : <ArrowUpDown className="h-3 w-3" />}
                    </button>
                  ) : column.header}
                </th>
              ))}</tr></thead>
              <tbody>
                {rows.length === 0 ? (
                  <tr><td colSpan={findingColumns.length} className="py-8 text-center text-sm" style={{ color: 'var(--t3)' }}>No findings match these filters.</td></tr>
                ) : rows.map((finding) => (
                  <tr key={finding.id}>
                    {findingColumns.map((column) => (
                      <td key={column.key} className={['algorithm', 'file', 'line'].includes(column.key) ? 'mono' : ''}>
                        {column.key === 'risk_tier' && finding.risk_tier
                          ? <span className={`badge badge-${finding.risk_tier.toLowerCase()}`}>{column.accessor(finding)}</span>
                          : column.accessor(finding) ?? '—'}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="px-4 py-2 text-right text-xs num" style={{ color: 'var(--t3)' }}>
            {rows.length} of {query.data?.total_on_page ?? 0} findings on this page
          </div>
        </div>
      )}
    </section>
  );
}
