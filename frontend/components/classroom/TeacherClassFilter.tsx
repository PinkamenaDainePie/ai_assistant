'use client';

import React from 'react';
import type { ClassInfo } from '../../lib/classroomApi';

type Props = {
  classes: ClassInfo[];
  classId: number | '';
  onClassIdChange: (id: number | '') => void;
  id?: string;
};

export function TeacherClassFilter({ classes, classId, onClassIdChange, id = 'filter-class' }: Props) {
  return (
    <div className="ui-field ui-field--inline">
      <label className="ui-label" htmlFor={id}>
        班级
      </label>
      <select
        id={id}
        className="ui-select"
        value={classId}
        onChange={(e) => onClassIdChange(e.target.value === '' ? '' : Number(e.target.value))}
      >
        <option value="">全部班级</option>
        {classes.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}
          </option>
        ))}
      </select>
    </div>
  );
}
