export async function createStory(storyData: any) {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/stories`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(storyData),
  })
  return res.json()
}
