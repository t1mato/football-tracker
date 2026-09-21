/** Mirrors app/formatting.py's player_age: age in whole years as of
 * today, correctly handling a birthday that hasn't happened yet this
 * year -- naive (today - dob) / 365 over-reports by a year for anyone
 * whose birthday is still ahead in the current calendar year.
 *
 * Parses the YYYY-MM-DD prefix directly rather than via `new Date(string)`,
 * which parses a bare date string ("2000-06-16") as UTC midnight but a
 * datetime string with no offset ("2000-06-16T00:00:00") as local time --
 * two different rules for similar-looking input. Explicit component
 * parsing is correct under both serialization formats.
 */
export function playerAge(dateOfBirth: string, today: Date = new Date()): number {
  const [dobYear, dobMonth, dobDay] = dateOfBirth
    .slice(0, 10)
    .split('-')
    .map(Number)
  const todayMonth = today.getMonth() + 1
  const todayDay = today.getDate()
  const hadBirthdayThisYear =
    todayMonth > dobMonth || (todayMonth === dobMonth && todayDay >= dobDay)
  return today.getFullYear() - dobYear - (hadBirthdayThisYear ? 0 : 1)
}
