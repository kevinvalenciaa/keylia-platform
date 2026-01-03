"use client";

import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ArrowLeft, ArrowRight, Video, Mic, ImageIcon, Upload, Check } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";

type ProjectType = "listing_tour" | "promo_video" | "infographic";

const contentTypes = [
  {
    id: "listing_tour" as const,
    name: "Listing Tour Video",
    description: "Cinematic property tour from photos with AI voiceover",
    icon: Video,
    color: "brand",
  },
  {
    id: "promo_video" as const,
    name: "Promo Video",
    description: "You on camera with property photos as B-roll",
    icon: Mic,
    color: "coral",
  },
  {
    id: "infographic" as const,
    name: "Infographic Post",
    description: "Branded graphics and carousels for feed & stories",
    icon: ImageIcon,
    color: "purple",
  },
];

function NewProjectForm() {
  const searchParams = useSearchParams();
  const initialType = searchParams.get("type") as ProjectType | null;
  
  const [step, setStep] = useState(initialType ? 2 : 1);
  const [projectType, setProjectType] = useState<ProjectType | null>(initialType);
  const [formData, setFormData] = useState({
    address: "",
    city: "",
    state: "",
    zipCode: "",
    price: "",
    bedrooms: "",
    bathrooms: "",
    sqft: "",
    status: "just_listed",
    features: [] as string[],
  });

  const handleTypeSelect = (type: ProjectType) => {
    setProjectType(type);
    setStep(2);
  };

  const steps = [
    { number: 1, title: "Content Type" },
    { number: 2, title: "Property Details" },
    { number: 3, title: "Upload Media" },
    { number: 4, title: "Style & Voice" },
    { number: 5, title: "Review" },
  ];

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/dashboard">
            <ArrowLeft className="h-5 w-5" />
          </Link>
        </Button>
        <div>
          <h1 className="text-2xl font-display font-bold">Create New Project</h1>
          <p className="text-muted-foreground">Step {step} of 5</p>
        </div>
      </div>

      {/* Progress Steps */}
      <div className="flex items-center justify-between mb-8">
        {steps.map((s, i) => (
          <div key={s.number} className="flex items-center">
            <div
              className={cn(
                "flex items-center justify-center h-8 w-8 rounded-full text-sm font-medium transition-colors",
                step >= s.number
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground"
              )}
            >
              {step > s.number ? <Check className="h-4 w-4" /> : s.number}
            </div>
            {i < steps.length - 1 && (
              <div
                className={cn(
                  "hidden sm:block w-16 lg:w-24 h-0.5 mx-2",
                  step > s.number ? "bg-primary" : "bg-muted"
                )}
              />
            )}
          </div>
        ))}
      </div>

      {/* Step 1: Choose Content Type */}
      {step === 1 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">What would you like to create?</h2>
          <div className="grid gap-4">
            {contentTypes.map((type) => (
              <Card
                key={type.id}
                className={cn(
                  "cursor-pointer transition-all hover:shadow-md",
                  projectType === type.id && "ring-2 ring-primary"
                )}
                onClick={() => handleTypeSelect(type.id)}
              >
                <CardContent className="flex items-center gap-4 p-6">
                  <div
                    className={cn(
                      "h-12 w-12 rounded-xl flex items-center justify-center",
                      type.color === "brand" && "bg-brand-100 text-brand-600",
                      type.color === "coral" && "bg-coral-100 text-coral-600",
                      type.color === "purple" && "bg-purple-100 text-purple-600"
                    )}
                  >
                    <type.icon className="h-6 w-6" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold">{type.name}</h3>
                    <p className="text-sm text-muted-foreground">
                      {type.description}
                    </p>
                  </div>
                  <ArrowRight className="h-5 w-5 text-muted-foreground" />
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Step 2: Property Details */}
      {step === 2 && (
        <Card>
          <CardHeader>
            <CardTitle>Property Details</CardTitle>
            <CardDescription>
              Tell us about the listing you're promoting
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Address */}
            <div className="space-y-4">
              <h3 className="text-sm font-medium">Address</h3>
              <Input
                placeholder="Street address"
                value={formData.address}
                onChange={(e) =>
                  setFormData({ ...formData, address: e.target.value })
                }
              />
              <div className="grid grid-cols-3 gap-4">
                <Input
                  placeholder="City"
                  value={formData.city}
                  onChange={(e) =>
                    setFormData({ ...formData, city: e.target.value })
                  }
                />
                <Input
                  placeholder="State"
                  value={formData.state}
                  onChange={(e) =>
                    setFormData({ ...formData, state: e.target.value })
                  }
                />
                <Input
                  placeholder="ZIP Code"
                  value={formData.zipCode}
                  onChange={(e) =>
                    setFormData({ ...formData, zipCode: e.target.value })
                  }
                />
              </div>
            </div>

            {/* Property Info */}
            <div className="space-y-4">
              <h3 className="text-sm font-medium">Property Information</h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div>
                  <label className="text-xs text-muted-foreground">Price</label>
                  <Input
                    placeholder="$450,000"
                    value={formData.price}
                    onChange={(e) =>
                      setFormData({ ...formData, price: e.target.value })
                    }
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Beds</label>
                  <Input
                    type="number"
                    placeholder="3"
                    value={formData.bedrooms}
                    onChange={(e) =>
                      setFormData({ ...formData, bedrooms: e.target.value })
                    }
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Baths</label>
                  <Input
                    type="number"
                    placeholder="2"
                    value={formData.bathrooms}
                    onChange={(e) =>
                      setFormData({ ...formData, bathrooms: e.target.value })
                    }
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Sq Ft</label>
                  <Input
                    type="number"
                    placeholder="2,100"
                    value={formData.sqft}
                    onChange={(e) =>
                      setFormData({ ...formData, sqft: e.target.value })
                    }
                  />
                </div>
              </div>
            </div>

            {/* Status */}
            <div className="space-y-4">
              <h3 className="text-sm font-medium">Listing Status</h3>
              <div className="flex flex-wrap gap-2">
                {[
                  { id: "just_listed", label: "Just Listed" },
                  { id: "for_sale", label: "For Sale" },
                  { id: "open_house", label: "Open House" },
                  { id: "pending", label: "Pending" },
                  { id: "just_sold", label: "Just Sold" },
                ].map((status) => (
                  <button
                    key={status.id}
                    type="button"
                    className={cn(
                      "px-4 py-2 rounded-full text-sm font-medium transition-colors",
                      formData.status === status.id
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted hover:bg-muted/80"
                    )}
                    onClick={() =>
                      setFormData({ ...formData, status: status.id })
                    }
                  >
                    {status.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Features */}
            <div className="space-y-4">
              <h3 className="text-sm font-medium">Key Features</h3>
              <div className="flex flex-wrap gap-2">
                {[
                  "Pool",
                  "Updated Kitchen",
                  "Smart Home",
                  "Solar",
                  "Garage",
                  "Hardwood Floors",
                  "Fireplace",
                  "View",
                  "New Roof",
                  "New HVAC",
                ].map((feature) => (
                  <button
                    key={feature}
                    type="button"
                    className={cn(
                      "px-3 py-1.5 rounded-full text-sm transition-colors",
                      formData.features.includes(feature)
                        ? "bg-brand-100 text-brand-700 border border-brand-200"
                        : "bg-muted hover:bg-muted/80"
                    )}
                    onClick={() => {
                      const features = formData.features.includes(feature)
                        ? formData.features.filter((f) => f !== feature)
                        : [...formData.features, feature];
                      setFormData({ ...formData, features });
                    }}
                  >
                    {formData.features.includes(feature) && (
                      <Check className="inline h-3 w-3 mr-1" />
                    )}
                    {feature}
                  </button>
                ))}
              </div>
            </div>

            {/* Navigation */}
            <div className="flex justify-between pt-4">
              <Button variant="outline" onClick={() => setStep(1)}>
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back
              </Button>
              <Button onClick={() => setStep(3)}>
                Continue
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 3: Upload Media */}
      {step === 3 && (
        <Card>
          <CardHeader>
            <CardTitle>Upload Property Photos</CardTitle>
            <CardDescription>
              Add 5-40 photos. We'll use AI to select the best shots for your content.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Upload Zone */}
            <div className="border-2 border-dashed rounded-xl p-12 text-center hover:bg-muted/50 transition-colors cursor-pointer">
              <div className="mx-auto w-12 h-12 rounded-xl bg-muted flex items-center justify-center mb-4">
                <Upload className="h-6 w-6 text-muted-foreground" />
              </div>
              <h3 className="font-medium mb-1">Drop photos here</h3>
              <p className="text-sm text-muted-foreground mb-4">
                or click to browse
              </p>
              <p className="text-xs text-muted-foreground">
                JPG, PNG, HEIC • Max 20MB each
              </p>
            </div>

            {/* Sample uploaded photos placeholder */}
            <div className="grid grid-cols-4 sm:grid-cols-6 gap-2">
              {Array.from({ length: 6 }).map((_, i) => (
                <div
                  key={i}
                  className="aspect-square rounded-lg bg-muted flex items-center justify-center"
                >
                  <ImageIcon className="h-6 w-6 text-muted-foreground/50" />
                </div>
              ))}
            </div>

            {/* Navigation */}
            <div className="flex justify-between pt-4">
              <Button variant="outline" onClick={() => setStep(2)}>
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back
              </Button>
              <Button onClick={() => setStep(4)}>
                Continue
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 4: Style & Voice */}
      {step === 4 && (
        <Card>
          <CardHeader>
            <CardTitle>Choose Your Style</CardTitle>
            <CardDescription>
              Customize the look and feel of your content
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-8">
            {/* Tone */}
            <div className="space-y-4">
              <h3 className="text-sm font-medium">Tone</h3>
              <div className="grid grid-cols-5 gap-3">
                {["Luxury", "Cozy", "Modern", "Minimal", "Bold"].map((tone) => (
                  <button
                    key={tone}
                    className="p-4 rounded-xl border-2 hover:border-primary transition-colors text-center"
                  >
                    <span className="text-sm font-medium">{tone}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Duration */}
            <div className="space-y-4">
              <h3 className="text-sm font-medium">Duration</h3>
              <div className="flex gap-3">
                {[
                  { sec: 15, label: "15s", sub: "Story" },
                  { sec: 30, label: "30s", sub: "Reel" },
                  { sec: 45, label: "45s", sub: "Extended" },
                  { sec: 60, label: "60s", sub: "Full Tour" },
                ].map((d) => (
                  <button
                    key={d.sec}
                    className="flex-1 p-4 rounded-xl border-2 hover:border-primary transition-colors text-center"
                  >
                    <span className="block text-lg font-semibold">{d.label}</span>
                    <span className="text-xs text-muted-foreground">{d.sub}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Voice */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium">AI Voiceover</h3>
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" defaultChecked className="rounded" />
                  Enabled
                </label>
              </div>
              <div className="grid grid-cols-3 gap-3">
                {["Female", "Male", "Neutral"].map((voice) => (
                  <button
                    key={voice}
                    className="p-3 rounded-xl border-2 hover:border-primary transition-colors"
                  >
                    {voice}
                  </button>
                ))}
              </div>
            </div>

            {/* Music */}
            <div className="space-y-4">
              <h3 className="text-sm font-medium">Background Music</h3>
              <div className="grid grid-cols-5 gap-3">
                {["Chill", "Upbeat", "Cinematic", "Piano", "Electronic"].map(
                  (music) => (
                    <button
                      key={music}
                      className="p-3 rounded-xl border-2 hover:border-primary transition-colors text-sm"
                    >
                      {music}
                    </button>
                  )
                )}
              </div>
            </div>

            {/* Navigation */}
            <div className="flex justify-between pt-4">
              <Button variant="outline" onClick={() => setStep(3)}>
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back
              </Button>
              <Button onClick={() => setStep(5)}>
                Generate Script
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 5: Review */}
      {step === 5 && (
        <Card>
          <CardHeader>
            <CardTitle>✨ Your AI Script is Ready</CardTitle>
            <CardDescription>
              Review and customize before generating your video
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Script Preview */}
            <div className="rounded-xl border overflow-hidden">
              <div className="bg-muted/50 px-4 py-2 border-b">
                <h3 className="text-sm font-medium">Storyboard Preview</h3>
              </div>
              <div className="divide-y">
                {[
                  {
                    scene: 1,
                    text: "Welcome to your dream home in Westwood Heights",
                    overlay: "JUST LISTED • $450,000",
                  },
                  {
                    scene: 2,
                    text: "This stunning 3-bed, 2-bath offers 2,100 square feet of modern living",
                    overlay: "3 BD • 2 BA • 2,100 SF",
                  },
                  {
                    scene: 3,
                    text: "The updated kitchen features quartz counters and stainless appliances",
                    overlay: "CHEF'S KITCHEN",
                  },
                  {
                    scene: 4,
                    text: "Step outside to your private pool oasis",
                    overlay: "POOL & SPA",
                  },
                  {
                    scene: 5,
                    text: "Schedule your private showing today!",
                    overlay: "Kevin Valencia • (555) 123-4567",
                  },
                ].map((scene) => (
                  <div key={scene.scene} className="flex gap-4 p-4">
                    <div className="w-16 h-16 rounded-lg bg-muted flex items-center justify-center shrink-0">
                      <span className="text-xs text-muted-foreground">
                        Scene {scene.scene}
                      </span>
                    </div>
                    <div className="flex-1">
                      <p className="text-sm mb-1">"{scene.text}"</p>
                      <p className="text-xs text-muted-foreground">
                        On-screen: {scene.overlay}
                      </p>
                    </div>
                    <Button variant="ghost" size="sm">
                      Edit
                    </Button>
                  </div>
                ))}
              </div>
            </div>

            {/* Caption Preview */}
            <div className="rounded-xl border p-4">
              <h3 className="text-sm font-medium mb-2">Suggested Caption</h3>
              <p className="text-sm text-muted-foreground mb-3">
                ✨ Just Listed in Westwood Heights! This stunning 3BD/2BA home is
                ready for its new owners... DM me for a private showing! 🏡
              </p>
              <p className="text-xs text-brand-600">
                #JustListed #WestwoodHeights #RealEstate #DreamHome #HomesForSale
              </p>
            </div>

            {/* Actions */}
            <div className="flex justify-between pt-4">
              <Button variant="outline" onClick={() => setStep(4)}>
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back
              </Button>
              <Button className="gradient-brand">
                🎬 Generate Video
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default function NewProjectPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center py-12">Loading...</div>}>
      <NewProjectForm />
    </Suspense>
  );
}
