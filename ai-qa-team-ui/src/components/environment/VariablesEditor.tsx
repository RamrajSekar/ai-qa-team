'use client';

import { Plus, Trash } from 'lucide-react';
import { Dispatch, SetStateAction } from 'react';

export interface VariablesEditorProps {
  items: [string, string][];
  onChange: Dispatch<SetStateAction<[string, string][]>> | ((items: [string, string][]) => void);
}

export default function VariablesEditor({ items, onChange }: VariablesEditorProps) {
  function updateKey(idx: number, key: string) {
    const copy = items.map((entry, i) =>
      i === idx ? [key, entry[1]] : entry
    ) as [string, string][];
    (onChange as (items: [string, string][]) => void)(copy);
  }

  function updateValue(idx: number, value: string) {
    const copy = items.map((entry, i) =>
      i === idx ? [entry[0], value] : entry
    ) as [string, string][];
    (onChange as (items: [string, string][]) => void)(copy);
  }

  function addRow() {
    const copy = [...items, ['', '']] as [string, string][];
    (onChange as (items: [string, string][]) => void)(copy);
  }

  function removeRow(idx: number) {
    const copy = items.filter((_, i) => i !== idx) as [string, string][];
    (onChange as (items: [string, string][]) => void)(copy);
  }

  return (
    <div>
      {items.length === 0 && (
        <p className='mb-2 text-sm text-gray-400'>
          No variables yet. Add entries like <code>basePath=/admin</code>.
        </p>
      )}

      {items.map(([key, value], idx) => (
        <div key={idx} className='mb-2 flex gap-2'>
          <input
            value={key}
            onChange={(e) => updateKey(idx, e.target.value)}
            className='w-1/3 rounded-md border border-gray-300 px-2 py-1 text-sm'
            placeholder='Key'
          />
          <input
            value={value}
            onChange={(e) => updateValue(idx, e.target.value)}
            className='flex-1 rounded-md border border-gray-300 px-2 py-1 text-sm'
            placeholder='Value'
          />
          <button
            type='button'
            onClick={() => removeRow(idx)}
            className='text-red-500 hover:text-red-600'
          >
            <Trash size={16} />
          </button>
        </div>
      ))}

      <button
        type='button'
        onClick={addRow}
        className='mt-2 inline-flex items-center gap-2 rounded-md border border-gray-300 px-3 py-1 text-xs hover:bg-gray-50'
      >
        <Plus size={14} /> Add variable
      </button>
    </div>
  );
}
