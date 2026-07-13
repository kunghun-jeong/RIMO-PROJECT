import React from 'react'
import { useState } from 'react';
import NaturalIntentForm from '../modals_components/natural-intent-form';
import './registration.css'

export default function Registration(props) {
  const [open, setOpen] = useState(false);
  const dark = props.mode === 'dark';

  if (open) {
    return (
      <div className='registration-space'>
        <button className={dark ? 'dark-back' : 'light-back'} onClick={() => setOpen(false)}>
          ← Back
        </button>
        <NaturalIntentForm mode={props.mode} />
      </div>
    );
  }

  return (
    <div className='registration'>
      <button className={dark ? 'dark-card' : 'light-card'} onClick={() => setOpen(true)}>
        <div className='hub-card-icon'>🗣️</div>
        <div className='hub-card-title'>Natural Language Command</div>
        <div className='hub-card-desc'>Control LIMO with natural language — movement, tracking, obstacle avoidance, and greetings.</div>
        <div className='hub-card-example'>e.g. "Find a person and greet them"</div>
      </button>
    </div>
  )
}
