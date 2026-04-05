'use strict';

const { Contract } = require('fabric-contract-api');

class ProvenanceContract extends Contract {
  async notarizeArtifact(ctx, artifactId, snapshotId, artifactType, sha256, signer, metadataJson) {
    const exists = await this.assetExists(ctx, artifactId);
    if (exists) {
      throw new Error(`Artifact ${artifactId} already exists`);
    }

    const asset = {
      artifactId,
      snapshotId,
      artifactType,
      sha256,
      signer,
      metadata: JSON.parse(metadataJson || '{}'),
      txId: ctx.stub.getTxID(),
      timestamp: new Date().toISOString(),
      docType: 'artifact'
    };

    await ctx.stub.putState(artifactId, Buffer.from(JSON.stringify(asset)));
    return JSON.stringify(asset);
  }

  async verifyArtifact(ctx, artifactId, sha256) {
    const data = await ctx.stub.getState(artifactId);
    if (!data || data.length === 0) {
      throw new Error(`Artifact ${artifactId} not found`);
    }
    const asset = JSON.parse(data.toString());
    return JSON.stringify({
      artifactId,
      ledgerSha256: asset.sha256,
      providedSha256: sha256,
      verified: asset.sha256 === sha256,
      txId: asset.txId
    });
  }

  async readArtifact(ctx, artifactId) {
    const data = await ctx.stub.getState(artifactId);
    if (!data || data.length === 0) {
      throw new Error(`Artifact ${artifactId} not found`);
    }
    return data.toString();
  }

  async assetExists(ctx, artifactId) {
    const data = await ctx.stub.getState(artifactId);
    return !!data && data.length > 0;
  }
}

module.exports = ProvenanceContract;
