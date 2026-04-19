import { useState, useRef } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Image as ImageIcon, Loader2, Save } from "lucide-react";
import { useRestaurantProfile, useUpdateRestaurantProfile } from "@/hooks/useRestaurantData";
import { resolveImageUrl } from "@/lib/restaurantApi";
import { useToast } from "@/hooks/use-toast";

const RestaurantSettings = () => {
  const { data: profile, isLoading } = useRestaurantProfile();
  const updateMutation = useUpdateRestaurantProfile();
  const { toast } = useToast();

  const [name, setName] = useState("");
  const [cuisineType, setCuisineType] = useState("");
  const [address, setAddress] = useState("");
  const [phone, setPhone] = useState("");
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [coverFile, setCoverFile] = useState<File | null>(null);
  const [logoPreview, setLogoPreview] = useState<string>("");
  const [coverPreview, setCoverPreview] = useState<string>("");
  const [initialized, setInitialized] = useState(false);

  const logoInputRef = useRef<HTMLInputElement>(null);
  const coverInputRef = useRef<HTMLInputElement>(null);

  // Initialize form from profile data
  if (profile && !initialized) {
    setName(profile.name || "");
    setCuisineType(profile.cuisine_type || "");
    setAddress(profile.address || "");
    setPhone(profile.phone || "");
    if (profile.logo) setLogoPreview(resolveImageUrl(profile.logo) || "");
    if (profile.cover_image) setCoverPreview(resolveImageUrl(profile.cover_image) || "");
    setInitialized(true);
  }

  const handleFileSelect = (type: "logo" | "cover", file: File) => {
    const url = URL.createObjectURL(file);
    if (type === "logo") {
      setLogoFile(file);
      setLogoPreview(url);
    } else {
      setCoverFile(file);
      setCoverPreview(url);
    }
  };

  const handleSave = () => {
    const data: Record<string, unknown> = { name, cuisine_type: cuisineType, address, phone };
    if (logoFile) data.logo = logoFile;
    if (coverFile) data.cover_image = coverFile;

    updateMutation.mutate(data, {
      onSuccess: (updatedProfile) => {
        toast({ title: "Settings saved!" });
        setLogoFile(null);
        setCoverFile(null);
        // Update previews from server response so new images render immediately
        if (updatedProfile.logo) {
          setLogoPreview(resolveImageUrl(updatedProfile.logo) || "");
        }
        if (updatedProfile.cover_image) {
          setCoverPreview(resolveImageUrl(updatedProfile.cover_image) || "");
        }
      },
      onError: (err) => {
        toast({ title: "Error", description: err.message, variant: "destructive" });
      },
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold font-heading mb-6">Restaurant Settings</h1>
      <Card className="p-6 shadow-card">
        <div className="space-y-5">
          {/* Cover Photo */}
          <div>
            <Label>Cover Photo</Label>
            <input ref={coverInputRef} type="file" accept="image/*" className="hidden" onChange={(e) => e.target.files?.[0] && handleFileSelect("cover", e.target.files[0])} />
            <div
              className="mt-1 border-2 border-dashed rounded-lg h-40 overflow-hidden cursor-pointer hover:border-primary transition-colors relative"
              onClick={() => coverInputRef.current?.click()}
            >
              {coverPreview ? (
                <img src={coverPreview} alt="Cover" className="w-full h-full object-cover" />
              ) : (
                <div className="flex flex-col items-center justify-center h-full">
                  <ImageIcon className="h-8 w-8 text-muted-foreground mb-2" />
                  <p className="text-sm text-muted-foreground">Click to upload cover photo</p>
                </div>
              )}
            </div>
          </div>

          {/* Logo */}
          <div>
            <Label>Restaurant Logo</Label>
            <input ref={logoInputRef} type="file" accept="image/*" className="hidden" onChange={(e) => e.target.files?.[0] && handleFileSelect("logo", e.target.files[0])} />
            <div className="mt-1 flex items-center gap-4">
              <div
                className="h-20 w-20 border-2 border-dashed rounded-lg overflow-hidden cursor-pointer hover:border-primary transition-colors flex items-center justify-center"
                onClick={() => logoInputRef.current?.click()}
              >
                {logoPreview ? (
                  <img src={logoPreview} alt="Logo" className="h-full w-full object-cover" />
                ) : (
                  <ImageIcon className="h-6 w-6 text-muted-foreground" />
                )}
              </div>
              <p className="text-sm text-muted-foreground">Click to upload logo (square recommended)</p>
            </div>
          </div>

          <div>
            <Label>Restaurant Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} className="mt-1" />
          </div>
          <div>
            <Label>Cuisine Type</Label>
            <Input value={cuisineType} onChange={(e) => setCuisineType(e.target.value)} placeholder="e.g. Indian, Chinese, Italian" className="mt-1" />
          </div>
          <div>
            <Label>Address</Label>
            <Textarea value={address} onChange={(e) => setAddress(e.target.value)} placeholder="Full restaurant address" className="mt-1" rows={2} />
          </div>
          <div>
            <Label>Phone Number</Label>
            <Input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+91 9876543210" className="mt-1" />
          </div>
          <Button variant="hero" className="w-full" onClick={handleSave} disabled={updateMutation.isPending}>
            {updateMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Save className="h-4 w-4 mr-2" />}
            Save Changes
          </Button>
        </div>
      </Card>
    </div>
  );
};

export default RestaurantSettings;
