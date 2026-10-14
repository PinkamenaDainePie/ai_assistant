import type { Character } from './types';

/** 可在「问策」面板出现、且已接好后端 /chat 的角色 */
export function getConsultableCharacters(characters: Character[]): Character[] {
  return characters.filter((c) => {
    if (c.faction === 'emperor') return false;
    if (c.consultable === false) return false;
    return Boolean((c.apiCharacterId || '').trim());
  });
}

export function resolveApiCharacterId(character: Character): string {
  return (character.apiCharacterId || '').trim();
}
