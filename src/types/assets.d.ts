declare module "*.asset.json" {
  const value: { url: string; asset_id: string; original_filename: string; content_type: string; size: number };
  export default value;
}
