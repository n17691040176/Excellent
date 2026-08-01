import rawRegions from 'province-city-china/dist/level.json'

function normalizeRegionTree(regions) {
  return regions.map((province) => {
    const children = Array.isArray(province.children) ? province.children : []
    const hasCityLevel = children.some((city) => Array.isArray(city.children) && city.children.length)
    const cities = hasCityLevel
      ? children.map((city) => ({
          name: city.name,
          children: Array.isArray(city.children) && city.children.length ? city.children : [city]
        }))
      : [{ name: province.name, children: children.length ? children : [province] }]
    return { name: province.name, children: cities }
  })
}

const regionTree = normalizeRegionTree(rawRegions)

export const regionOptions = regionTree.map((province) => ({
  value: province.name,
  label: province.name,
  children: province.children.map((city) => ({
    value: city.name,
    label: city.name,
    children: city.children.map((district) => ({
      value: district.name,
      label: district.name
    }))
  }))
}))

export function findRegionPath(provinceName, cityName, districtName = '') {
  const province = regionTree.find((item) => item.name === provinceName)
  const city = province?.children.find((item) => item.name === cityName)
  if (!province || !city) return []
  if (!districtName) return [province.name, city.name]
  const district = city.children.find((item) => item.name === districtName)
  return district ? [province.name, city.name, district.name] : []
}
