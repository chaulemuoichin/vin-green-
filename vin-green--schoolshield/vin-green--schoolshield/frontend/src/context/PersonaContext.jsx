import { createContext, useContext, useState } from 'react'

const PersonaCtx = createContext({ persona: 'school', setPersona: () => {} })

export const usePersona = () => useContext(PersonaCtx)

export function PersonaProvider({ children }) {
  const [persona, setPersona] = useState('school')
  return (
    <PersonaCtx.Provider value={{ persona, setPersona }}>
      {children}
    </PersonaCtx.Provider>
  )
}
