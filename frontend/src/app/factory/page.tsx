"use client";

import React, { useRef, useEffect, useState, useCallback } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

interface MachineData {
    machineId: string;
    status: string;
    airTemp: number;
    torque: number;
}

export default function Factory3D() {
    const mountRef = useRef<HTMLDivElement>(null);
    const [machines, setMachines] = useState<MachineData[]>([]);
    const [hovered, setHovered] = useState<MachineData | null>(null);
    const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
    const machineMapRef = useRef<Map<string, THREE.Mesh>>(new Map());
    const sceneRef = useRef<THREE.Scene | null>(null);

    // Fetch machine data
    useEffect(() => {
        const fetchData = async () => {
            try {
                const res = await fetch("/api/states");
                if (res.ok) {
                    const data = await res.json();
                    setMachines(data);
                }
            } catch (e) { console.error(e); }
        };
        fetchData();
        const interval = setInterval(fetchData, 5000);
        return () => clearInterval(interval);
    }, []);

    // Three.js scene setup
    useEffect(() => {
        if (!mountRef.current) return;

        const container = mountRef.current;
        const width = container.clientWidth;
        const height = container.clientHeight;

        // ── Scene ──
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x0a0f1a);
        scene.fog = new THREE.FogExp2(0x0a0f1a, 0.003);
        sceneRef.current = scene;

        // ── Camera ──
        const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);
        camera.position.set(60, 55, 60);
        camera.lookAt(0, 0, 0);

        // ── Renderer ──
        const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.setSize(width, height);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        container.appendChild(renderer.domElement);

        // ── Controls ──
        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;
        controls.maxPolarAngle = Math.PI / 2.1;
        controls.minDistance = 10;
        controls.maxDistance = 200;

        // ── Lighting ──
        const ambientLight = new THREE.AmbientLight(0x404060, 0.6);
        scene.add(ambientLight);

        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(20, 30, 10);
        directionalLight.castShadow = true;
        directionalLight.shadow.mapSize.width = 2048;
        directionalLight.shadow.mapSize.height = 2048;
        scene.add(directionalLight);

        const pointLight1 = new THREE.PointLight(0x50fa7b, 0.3, 60);
        pointLight1.position.set(-10, 15, -10);
        scene.add(pointLight1);

        const pointLight2 = new THREE.PointLight(0xff5252, 0.3, 60);
        pointLight2.position.set(10, 15, 10);
        scene.add(pointLight2);

        // ── Factory Floor ──
        const floorGeo = new THREE.PlaneGeometry(140, 140);
        const floorMat = new THREE.MeshStandardMaterial({
            color: 0x141b2d,
            roughness: 0.85,
            metalness: 0.1,
        });
        const floor = new THREE.Mesh(floorGeo, floorMat);
        floor.rotation.x = -Math.PI / 2;
        floor.receiveShadow = true;
        scene.add(floor);

        // Grid helper on the floor
        const grid = new THREE.GridHelper(140, 70, 0x1e293b, 0x1e293b);
        grid.position.y = 0.01;
        scene.add(grid);

        // ── Raycaster for hover ──
        const raycaster = new THREE.Raycaster();
        const mouse = new THREE.Vector2();

        const onMouseMove = (event: MouseEvent) => {
            const rect = container.getBoundingClientRect();
            mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
            mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
            setTooltipPos({ x: event.clientX - rect.left, y: event.clientY - rect.top });
        };
        container.addEventListener("mousemove", onMouseMove);

        // ── Animation Loop ──
        let frameId: number;
        const clock = new THREE.Clock();
        const animate = () => {
            frameId = requestAnimationFrame(animate);
            const elapsed = clock.getElapsedTime();

            // Hover detection
            raycaster.setFromCamera(mouse, camera);
            const meshes = Array.from(machineMapRef.current.values());
            const intersects = raycaster.intersectObjects(meshes);
            if (intersects.length > 0) {
                const meshName = intersects[0].object.name;
                const machineData = (intersects[0].object as any).userData?.machineData;
                if (machineData) {
                    setHovered(machineData);
                }
                container.style.cursor = "pointer";
            } else {
                setHovered(null);
                container.style.cursor = "grab";
            }

            // Subtle animation for critical machines (pulsing glow)
            machineMapRef.current.forEach((mesh) => {
                if (mesh.userData?.isCritical) {
                    const scale = 1 + Math.sin(elapsed * 3) * 0.05;
                    mesh.scale.y = scale;
                }
            });

            controls.update();
            renderer.render(scene, camera);
        };
        animate();

        // ── Resize ──
        const handleResize = () => {
            const w = container.clientWidth;
            const h = container.clientHeight;
            camera.aspect = w / h;
            camera.updateProjectionMatrix();
            renderer.setSize(w, h);
        };
        window.addEventListener("resize", handleResize);

        return () => {
            cancelAnimationFrame(frameId);
            window.removeEventListener("resize", handleResize);
            container.removeEventListener("mousemove", onMouseMove);
            renderer.dispose();
            controls.dispose();
            if (container.contains(renderer.domElement)) {
                container.removeChild(renderer.domElement);
            }
        };
    }, []);

    // Update machine meshes when data changes
    useEffect(() => {
        if (!sceneRef.current || machines.length === 0) return;
        const scene = sceneRef.current;

        // Clear old machines
        machineMapRef.current.forEach((mesh) => scene.remove(mesh));
        machineMapRef.current.clear();

        // Render ALL machines
        const cols = Math.ceil(Math.sqrt(machines.length));
        const spacing = 1.6;
        const offsetX = -(cols * spacing) / 2;
        const offsetZ = -(Math.ceil(machines.length / cols) * spacing) / 2;

        // Shared materials for performance (only 2 draw-call groups)
        const healthyMat = new THREE.MeshStandardMaterial({
            color: 0x50fa7b, roughness: 0.4, metalness: 0.6,
            emissive: 0x003300, emissiveIntensity: 0.1,
        });
        const criticalMat = new THREE.MeshStandardMaterial({
            color: 0xff5252, roughness: 0.4, metalness: 0.6,
            emissive: 0x660000, emissiveIntensity: 0.5,
        });

        machines.forEach((m, i) => {
            const col = i % cols;
            const row = Math.floor(i / cols);
            const isCritical = m.status === "CRITICAL";

            const h = 0.6 + (parseFloat(String(m.torque)) || 0) / 50;
            const geo = new THREE.BoxGeometry(1.2, Math.max(h, 0.3), 1.2);
            const mesh = new THREE.Mesh(geo, isCritical ? criticalMat : healthyMat);
            mesh.position.set(
                offsetX + col * spacing,
                Math.max(h, 0.3) / 2,
                offsetZ + row * spacing
            );
            mesh.castShadow = false; // disable per-object shadows for perf
            mesh.name = m.machineId;
            mesh.userData = { machineData: m, isCritical };

            scene.add(mesh);
            machineMapRef.current.set(m.machineId, mesh);
        });
    }, [machines]);


    return (
        <main className="relative w-screen h-screen overflow-hidden bg-[#0a0f1a]">
            {/* Top Bar */}
            <div className="absolute top-0 left-0 right-0 z-10 flex items-center gap-4 px-6 py-3 bg-gradient-to-b from-[#0a0f1a] to-transparent">
                <Link href="/" className="flex items-center gap-2 text-sm text-content-secondary hover:text-content-primary transition-colors">
                    <ArrowLeft size={16} />
                    Back to Dashboard
                </Link>
                <div className="h-4 w-px bg-border-subtle" />
                <h1 className="text-sm font-bold uppercase tracking-wider text-content-primary">
                    3D Factory Floor
                </h1>
                <span className="text-xs text-content-tertiary font-mono ml-auto">
                    {machines.length} machines · Orbit: drag · Zoom: scroll
                </span>
            </div>

            {/* Legend */}
            <div className="absolute bottom-6 left-6 z-10 flex items-center gap-4 bg-[#141b2d]/90 backdrop-blur-sm border border-border-subtle rounded-lg px-4 py-2.5 text-xs font-mono">
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-sm bg-[#50fa7b]" />
                    <span className="text-content-secondary">Healthy</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-sm bg-[#ff5252] animate-pulse" />
                    <span className="text-content-secondary">Critical</span>
                </div>
                <div className="h-4 w-px bg-border-subtle" />
                <span className="text-content-tertiary">Height = Torque (Nm)</span>
            </div>

            {/* Tooltip */}
            {hovered && (
                <div
                    className="absolute z-20 pointer-events-none bg-[#141b2d]/95 backdrop-blur-sm border border-border-subtle rounded-lg px-4 py-3 text-xs font-mono shadow-2xl"
                    style={{
                        left: tooltipPos.x + 16,
                        top: tooltipPos.y - 8,
                        transform: "translateY(-100%)",
                    }}
                >
                    <div className="font-bold text-sm mb-1.5">{hovered.machineId}</div>
                    <div className="flex flex-col gap-1 text-content-secondary">
                        <div className="flex justify-between gap-6">
                            <span>Status:</span>
                            <span className={hovered.status === "CRITICAL" ? "text-[#ff5252] font-bold" : "text-[#50fa7b]"}>
                                {hovered.status}
                            </span>
                        </div>
                        <div className="flex justify-between gap-6">
                            <span>Air Temp:</span>
                            <span>{parseFloat(String(hovered.airTemp)).toFixed(1)} K</span>
                        </div>
                        <div className="flex justify-between gap-6">
                            <span>Torque:</span>
                            <span>{parseFloat(String(hovered.torque)).toFixed(1)} Nm</span>
                        </div>
                    </div>
                </div>
            )}

            {/* Three.js Canvas */}
            <div ref={mountRef} className="w-full h-full" />
        </main>
    );
}
