/** Mirrors app/formatting.py's player_age: age in whole years as of
 * today, correctly handling a birthday that hasn't happened yet this
 * year -- naive (today - dob) / 365 over-reports by a year for anyone
 * whose birthday is still ahead in the current calendar year.
 */
export function playerAge(dateOfBirth: string, today: Date = new Date()): number {
  const dob = new Date(dateOfBirth)
  const hadBirthdayThisYear =
    today.getMonth() > dob.getMonth() ||
    (today.getMonth() === dob.getMonth() && today.getDate() >= dob.getDate())
  return today.getFullYear() - dob.getFullYear() - (hadBirthdayThisYear ? 0 : 1)
}
