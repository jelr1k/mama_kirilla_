import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import CategoryTabs from './CategoryTabs';

describe('CategoryTabs component', () => {
  const categories = [
    { id: 'all', label: 'Все' },
    { id: 'voice', label: 'Голос' },
    { id: 'system', label: 'Система' },
  ];

  it('renders tabs and indicates active tab', () => {
    const onChange = vi.fn();
    render(
      <CategoryTabs
        categories={categories}
        activeId="voice"
        onChange={onChange}
      />
    );

    const activeBtn = screen.getByRole('button', { name: 'Голос' });
    expect(activeBtn).toHaveClass('active');

    const otherBtn = screen.getByRole('button', { name: 'Все' });
    expect(otherBtn).not.toHaveClass('active');
  });

  it('calls onChange with category id when clicked', () => {
    const onChange = vi.fn();
    render(
      <CategoryTabs
        categories={categories}
        activeId="all"
        onChange={onChange}
      />
    );

    const systemBtn = screen.getByRole('button', { name: 'Система' });
    fireEvent.click(systemBtn);

    expect(onChange).toHaveBeenCalledWith('system');
  });
});
